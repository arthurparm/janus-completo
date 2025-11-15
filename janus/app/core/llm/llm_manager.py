import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import random
import httpx
from openai import OpenAI

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from prometheus_client import Counter, Histogram, Gauge
from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker, CircuitOpenError

# Métricas
LLM_ROUTER_COUNTER = Counter(
    "llm_router_model_selected_total",
    "Contador para os modelos selecionados pelo roteador dinâmico",
    ["role", "priority", "model_name", "provider"]
)
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total de requisições ao provedor LLM",
    ["provider", "model", "role", "outcome", "exception_type"],
)
LLM_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Latência por requisição LLM",
    ["provider", "model", "role", "outcome"],
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Tokens contabilizados (aprox.) por direção",
    ["provider", "model", "role", "direction"],
)

logger = logging.getLogger(__name__)


# --- Configuração de Cache e Resiliência ---

@dataclass
class CachedLLM:
    instance: BaseChatModel
    created_at: datetime
    provider: str
    model: str
    consecutive_failures: int = 0


_llm_pool: Dict[str, list[CachedLLM]] = {}
_MAX_CACHE_FAILURES = 3
LLM_POOL_SIZE = Gauge(
    "llm_pool_size",
    "Tamanho do pool por provider/model",
    ["provider", "model"],
)
LLM_POOL_HITS = Counter(
    "llm_pool_hits_total",
    "Hits de pool por provider/model",
    ["provider", "model"],
)
LLM_POOL_MISSES = Counter(
    "llm_pool_misses_total",
    "Misses de pool por provider/model",
    ["provider", "model"],
)
LLM_POOL_EVICTIONS = Counter(
    "llm_pool_evictions_total",
    "Evicções de pool por provider/model",
    ["provider", "model", "reason"],
)
LLM_POOL_WARMS = Counter(
    "llm_pool_warm_total",
    "Instâncias pré-aquecidas por provider/model",
    ["provider", "model"],
)

# Circuit Breakers por provedor para isolar falhas
_provider_circuit_breakers: Dict[str, CircuitBreaker] = {
    provider: CircuitBreaker(
        failure_threshold=settings.LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=settings.LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    )
    for provider in ["ollama", "openai", "google_gemini", "unknown"]
}


# --- P4: Orçamentação, Preços e Seleção Adaptativa ---

@dataclass
class ProviderPricing:
    input_per_1k_usd: float
    output_per_1k_usd: float


@dataclass
class ProviderStats:
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.success_count / max(1, self.total_requests)

    @property
    def avg_latency(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.total_latency_seconds / max(1, self.total_requests)


@dataclass
class ModelStats:
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.success_count / max(1, self.total_requests)

    @property
    def avg_latency(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.total_latency_seconds / max(1, self.total_requests)


# Pricing por provedor (valores padrão via settings; Ollama ~ 0)
_provider_pricing: Dict[str, ProviderPricing] = {
    "openai": ProviderPricing(
        input_per_1k_usd=settings.OPENAI_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.OPENAI_COST_PER_1K_OUTPUT_USD,
    ),
    "google_gemini": ProviderPricing(
        input_per_1k_usd=settings.GEMINI_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.GEMINI_COST_PER_1K_OUTPUT_USD,
    ),
    "ollama": ProviderPricing(
        input_per_1k_usd=settings.OLLAMA_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.OLLAMA_COST_PER_1K_OUTPUT_USD,
    ),
}

# Orçamentos mensais por provedor
_provider_budgets_usd: Dict[str, float] = {
    "openai": settings.OPENAI_MONTHLY_BUDGET_USD,
    "google_gemini": settings.GEMINI_MONTHLY_BUDGET_USD,
    "ollama": settings.OLLAMA_MONTHLY_BUDGET_USD,
}

# Rastreamento de gastos acumulados
_provider_spend_usd: Dict[str, float] = {"openai": 0.0, "google_gemini": 0.0, "ollama": 0.0}

# Fatores de penalização por modelo (>=1.0). Quanto maior, menos preferido.
_model_penalty_factors: Dict[str, Dict[str, float]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
}

# EMA dinâmica de expected_k por papel (ktokens). Inicializa a partir das configurações.
_expected_k_ema_by_role: Dict[str, float] = {}
for _role_key, _k in getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).items():
    try:
        _expected_k_ema_by_role[_role_key] = float(_k)
    except Exception:
        _expected_k_ema_by_role[_role_key] = 2.0

# Orçamentos diários multitenant (USD)
_tenant_user_daily_budget_usd: float = getattr(settings, "TENANT_USER_DAILY_BUDGET_USD", 0.0) or 0.0
_tenant_project_daily_budget_usd: float = getattr(settings, "TENANT_PROJECT_DAILY_BUDGET_USD", 0.0) or 0.0

# Rastreamento de gastos por usuário/projeto (reset diário)
_tenant_user_spend_usd: Dict[str, Dict[str, Any]] = {}
_tenant_project_spend_usd: Dict[str, Dict[str, Any]] = {}

# Estatísticas observadas para seleção adaptativa
_provider_stats: Dict[str, ProviderStats] = {
    "openai": ProviderStats(),
    "google_gemini": ProviderStats(),
    "ollama": ProviderStats(),
}

# Estatísticas por modelo
_model_stats: Dict[str, Dict[str, ModelStats]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
}

# Métricas de orçamento e seleção
LLM_PROVIDER_SPEND_USD = Counter(
    "llm_provider_spend_usd_total",
    "Gasto acumulado em USD por provedor",
    ["provider", "category"],
)
LLM_PROVIDER_BUDGET_REMAINING = Gauge(
    "llm_provider_budget_remaining_usd",
    "Orçamento restante em USD por provedor",
    ["provider"],
)
LLM_SELECTION_SCORE = Gauge(
    "llm_selection_score",
    "Score de seleção adaptativa por provedor",
    ["priority", "provider"],
)

LLM_MODEL_SELECTION_SCORE = Gauge(
    "llm_model_selection_score",
    "Score de seleção adaptativa por modelo",
    ["priority", "provider", "model"],
)

LLM_EXPECTED_COST_USD = Gauge(
    "llm_expected_cost_usd",
    "Custo esperado (USD) por candidato antes da seleção",
    ["priority", "provider", "model", "role"],
)

# Métricas adicionais para economia dinâmica
LLM_EXPECTED_KTOKENS_GAUGE = Gauge(
    "llm_expected_ktokens_by_role",
    "EMA de expected_k (ktokens) por papel",
    ["role"],
)
LLM_TENANT_SPEND_USD = Counter(
    "llm_tenant_spend_usd_total",
    "Gasto acumulado em USD por tenant",
    ["kind", "id"],
)
LLM_COST_DEVIATION_USD = Gauge(
    "llm_cost_deviation_usd",
    "Desvio do custo real vs estimado (USD) por candidato",
    ["provider", "model", "role"],
)
LLM_EXPLORATION_DECISIONS = Counter(
    "llm_exploration_decisions_total",
    "Contagem de decisões de exploração na seleção",
    ["role", "priority"],
)

# Inicializa gauge de expected_k para papéis conhecidos
try:
    for rk, val in _expected_k_ema_by_role.items():
        LLM_EXPECTED_KTOKENS_GAUGE.labels(role=rk).set(val)
except Exception:
    pass


def _budget_remaining(provider: str) -> float:
    budget = _provider_budgets_usd.get(provider, 0.0)
    spend = _provider_spend_usd.get(provider, 0.0)
    return max(0.0, budget - spend)


def _budget_allows(provider: str) -> bool:
    # Orçamento 0.0 implica sem custo/sem controle (ex.: Ollama)
    budget = _provider_budgets_usd.get(provider, 0.0)
    if budget <= 0.0:
        return True
    return _budget_remaining(provider) > 0.0


def _circuit_closed(provider: str) -> bool:
    cb = _provider_circuit_breakers.get(provider)
    if not cb:
        return True
    try:
        return not cb.is_open()
    except Exception:
        return True


def _normalize(values):
    # Evita divisão por zero; retorna lista de valores normalizados [0..1]
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [1.0 for _ in values]
    return [(v - min_v) / (max_v - min_v) for v in values]


def _get_model_pricing(provider: str, model_name: str) -> ProviderPricing:
    try:
        if provider == "openai":
            mp = settings.OPENAI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(mp.get("input_per_1k_usd", settings.OPENAI_COST_PER_1K_INPUT_USD),
                                       mp.get("output_per_1k_usd", settings.OPENAI_COST_PER_1K_OUTPUT_USD))
            return ProviderPricing(settings.OPENAI_COST_PER_1K_INPUT_USD, settings.OPENAI_COST_PER_1K_OUTPUT_USD)
        if provider == "google_gemini":
            mp = settings.GEMINI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(mp.get("input_per_1k_usd", settings.GEMINI_COST_PER_1K_INPUT_USD),
                                       mp.get("output_per_1k_usd", settings.GEMINI_COST_PER_1K_OUTPUT_USD))
            return ProviderPricing(settings.GEMINI_COST_PER_1K_INPUT_USD, settings.GEMINI_COST_PER_1K_OUTPUT_USD)
        # ollama
        return ProviderPricing(settings.OLLAMA_COST_PER_1K_INPUT_USD, settings.OLLAMA_COST_PER_1K_OUTPUT_USD)
    except Exception:
        return ProviderPricing(0.0, 0.0)


def _today_str() -> str:
    try:
        return datetime.utcnow().strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _reset_if_new_day(spend_map: Dict[str, Dict[str, Any]]):
    today = _today_str()
    for k, v in list(spend_map.items()):
        if v.get("date") != today:
            spend_map[k] = {"date": today, "usd": 0.0}


def _tenant_budget_remaining(kind: str, id_: Optional[str]) -> float:
    if not id_:
        return float("inf")
    today = _today_str()
    if kind == "user":
        budget = _tenant_user_daily_budget_usd
        entry = _tenant_user_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_user_spend_usd[id_]
        return max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0)) if budget > 0 else float("inf")
    else:  # project
        budget = _tenant_project_daily_budget_usd
        entry = _tenant_project_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_project_spend_usd[id_]
        return max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0)) if budget > 0 else float("inf")


def _register_tenant_spend(kind: str, id_: Optional[str], cost_usd: float):
    if not id_:
        return
    today = _today_str()
    cost_usd = max(0.0, float(cost_usd))
    if kind == "user":
        entry = _tenant_user_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
        _tenant_user_spend_usd[id_]["usd"] = (_tenant_user_spend_usd[id_]["usd"] or 0.0) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="user", id=id_).inc(cost_usd)
        except Exception:
            pass
    else:
        entry = _tenant_project_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
        _tenant_project_spend_usd[id_]["usd"] = (_tenant_project_spend_usd[id_]["usd"] or 0.0) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="project", id=id_).inc(cost_usd)
        except Exception:
            pass


class ModelRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"


class ModelPriority(Enum):
    LOCAL_ONLY = "local_only"
    FAST_AND_CHEAP = "fast_and_cheap"
    HIGH_QUALITY = "high_quality"


# --- Funções de Validação e Health Check ---

def _validate_gemini_key(key: Optional[str]) -> bool:
    if not key or not key.startswith("AIza") or len(key) < 30:
        logger.warning("GEMINI_API_KEY parece inválido.")
        return False
    return True


def _validate_openai_key(key: Optional[str]) -> bool:
    if not key or not key.startswith("sk-") or len(key) < 20:
        logger.warning("OPENAI_API_KEY parece inválido.")
        return False
    return True


def _health_check_ollama(llm: ChatOllama, timeout_s: int = 30) -> bool:
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ollama_health")
        future = executor.submit(llm.invoke, "ping")
        future.result(timeout=timeout_s)
        logger.debug("Health check Ollama passou.")
        return True
    except Exception as e:
        logger.error(f"Health check Ollama falhou: {e}", exc_info=isinstance(e, FuturesTimeoutError))
        return False
    finally:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)


# --- Gerenciamento de Cache ---

def _pool_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"

def _get_from_pool(provider: str, model: str) -> Optional[BaseChatModel]:
    key = _pool_key(provider, model)
    pool = _llm_pool.get(key, [])
    if not pool:
        try:
            LLM_POOL_MISSES.labels(provider, model).inc()
        except Exception:
            pass
        return None
    now = datetime.now()
    ttl = int(getattr(settings, "LLM_POOL_TTL_SECONDS", getattr(settings, "LLM_CACHE_TTL_SECONDS", 3600)) or 3600)
    valid = []
    evicted = 0
    for item in pool:
        age = (now - item.created_at).total_seconds()
        if age > ttl or item.consecutive_failures >= _MAX_CACHE_FAILURES:
            evicted += 1
            try:
                LLM_POOL_EVICTIONS.labels(provider, model, "ttl" if age > ttl else "failures").inc()
            except Exception:
                pass
        else:
            valid.append(item)
    _llm_pool[key] = valid
    if not valid:
        try:
            LLM_POOL_MISSES.labels(provider, model).inc()
            LLM_POOL_SIZE.labels(provider, model).set(0)
        except Exception:
            pass
        return None
    inst = valid[0].instance
    try:
        LLM_POOL_HITS.labels(provider, model).inc()
        LLM_POOL_SIZE.labels(provider, model).set(len(valid))
    except Exception:
        pass
    return inst


def _add_to_pool(provider: str, model: str, llm: BaseChatModel):
    key = _pool_key(provider, model)
    pool = _llm_pool.get(key) or []
    max_size = int(getattr(settings, "LLM_POOL_MAX_SIZE", 4) or 4)
    if len(pool) < max_size:
        pool.append(CachedLLM(instance=llm, created_at=datetime.now(), provider=provider, model=model))
        _llm_pool[key] = pool
    else:
        _llm_pool[key] = pool
    try:
        LLM_POOL_SIZE.labels(provider, model).set(len(_llm_pool[key]))
    except Exception:
        pass


def invalidate_cache(provider: Optional[str] = None):
    if provider:
        keys_to_remove = [k for k in list(_llm_pool.keys()) if k.startswith(f"{provider}:")]
        for key in keys_to_remove:
            del _llm_pool[key]
        logger.info(f"Pool invalidado para provider: {provider}")
    else:
        _llm_pool.clear()
        logger.info("Pool de LLMs completamente invalidado.")

def warm_llm_pool(specs: Optional[list[str]] = None) -> Dict[str, int]:
    warmed: Dict[str, int] = {}
    items = specs or list(getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or [])
    for spec in items:
        try:
            provider, model = spec.split(":", 1)
            provider = provider.strip()
            model = model.strip()
            if _get_from_pool(provider, model):
                continue
            if provider == "ollama":
                mk: Dict[str, Any] = {}
                if settings.OLLAMA_NUM_CTX: mk["num_ctx"] = settings.OLLAMA_NUM_CTX
                if settings.OLLAMA_NUM_THREAD: mk["num_thread"] = settings.OLLAMA_NUM_THREAD
                if settings.OLLAMA_NUM_BATCH: mk["num_batch"] = settings.OLLAMA_NUM_BATCH
                if settings.OLLAMA_GPU_LAYERS: mk["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
                if settings.OLLAMA_KEEP_ALIVE: mk["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
                llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=model, temperature=0, model_kwargs=mk)
                if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
                    continue
                _add_to_pool("ollama", model, llm)
            elif provider == "openai":
                if not _validate_openai_key(getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()):
                    continue
                llm = ChatOpenAI(model=model, temperature=0, client=_get_openai_client())
                _add_to_pool("openai", model, llm)
            elif provider == "google_gemini":
                if not _validate_gemini_key(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()):
                    continue
                llm = ChatGoogleGenerativeAI(model=model, temperature=0,
                                             google_api_key=(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)() or None))
                _add_to_pool("google_gemini", model, llm)
            else:
                continue
            key = _pool_key(provider, model)
            warmed[key] = warmed.get(key, 0) + 1
            try:
                LLM_POOL_WARMS.labels(provider, model).inc()
            except Exception:
                pass
        except Exception:
            pass
    return warmed


# --- Roteador Dinâmico de LLM (get_llm) ---

def get_llm(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY,
        cache_key: str = "",
        exclude_providers: Optional[list[str]] = None,
        config: Optional[Dict[str, Any]] = None
) -> BaseChatModel:
    """Obtém uma instância de um modelo de linguagem com base no papel e na prioridade.
    Suporta overrides via configuração (provider/model/temperature/exclude_providers/priority).
    """
    # Overrides por configuração dinâmica
    try:
        if config:
            prio = config.get("priority")
            if prio:
                try:
                    priority = prio if isinstance(prio, ModelPriority) else ModelPriority[str(prio)]
                except Exception:
                    try:
                        priority = ModelPriority[prio]
                    except Exception:
                        pass
            cfg_excl = config.get("exclude_providers") or []
            if cfg_excl:
                exclude_providers = list(set((exclude_providers or []) + list(cfg_excl)))
            forced_cache = config.get("cache_key")
            if forced_cache:
                cache_key = forced_cache
            provider = config.get("provider")
            model = config.get("model")
            temperature = float(config.get("temperature", 0))
            if provider and model:
                if not cache_key:
                    cache_key = f"forced_{provider}_{model}_{role.value}"
                pooled = _get_from_pool(provider, model)
                if pooled:
                    return pooled
                if exclude_providers and provider in exclude_providers:
                    logger.warning(f"Provedor '{provider}' excluído por configuração; ignorando override.")
                else:
                    try:
                        if provider == "ollama":
                            model_kwargs: Dict[str, Any] = {}
                            if settings.OLLAMA_NUM_CTX: model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
                            if settings.OLLAMA_NUM_THREAD: model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
                            if settings.OLLAMA_NUM_BATCH: model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
                            if settings.OLLAMA_GPU_LAYERS: model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
                            if settings.OLLAMA_KEEP_ALIVE: model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
                            llm = ChatOllama(
                                base_url=settings.OLLAMA_HOST,
                                model=model,
                                temperature=temperature,
                                model_kwargs=model_kwargs,
                            )
                            if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
                                raise RuntimeError(f"Health check falhou para modelo '{model}'")
                            LLM_ROUTER_COUNTER.labels(role.value, priority.value, model, "ollama").inc()
                            _add_to_pool("ollama", model, llm)
                            return llm
                        elif provider == "openai":
                            if not _validate_openai_key(
                                    getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()):
                                raise RuntimeError("OPENAI_API_KEY inválida ou ausente.")
                            llm = ChatOpenAI(model=model, temperature=temperature, client=_get_openai_client())
                            LLM_ROUTER_COUNTER.labels(role.value, priority.value, model, "openai").inc()
                            _add_to_pool("openai", model, llm)
                            return llm
                        elif provider == "google_gemini":
                            if not _validate_gemini_key(
                                    getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()):
                                raise RuntimeError("GEMINI_API_KEY inválida ou ausente.")
                            llm = ChatGoogleGenerativeAI(
                                model=model,
                                temperature=temperature,
                                google_api_key=(getattr(settings.GEMINI_API_KEY, 'get_secret_value',
                                                        lambda: None)() or None),
                            )
                            LLM_ROUTER_COUNTER.labels(role.value, priority.value, model, "google_gemini").inc()
                            _add_to_pool("google_gemini", model, llm)
                            return llm
                        else:
                            logger.warning(f"Provider override desconhecido: {provider}")
                    except Exception as e:
                        logger.error(f"Falha ao aplicar override de LLM: {e}", exc_info=True)
                        # Continua para a seleção padrão
    except Exception:
        pass

    if not cache_key:
        cache_key = f"{role.value}_{priority.value}"

    pooled_local = _get_from_pool("ollama", local_model_name) if priority == ModelPriority.LOCAL_ONLY else None
    if pooled_local:
        return pooled_local

    # Mapeamento de papéis para modelos locais
    model_map = {
        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
    }
    local_model_name = model_map.get(role, settings.OLLAMA_ORCHESTRATOR_MODEL)

    # Estratégia 1: Prioridade é o Cérebro Soberano Local
    if priority == ModelPriority.LOCAL_ONLY:
        try:
            # Bloqueia se provedor local estiver excluído
            if exclude_providers and "ollama" in exclude_providers:
                raise RuntimeError("Provedor local 'ollama' está excluído para esta seleção.")
            # Model kwargs para tunar desempenho do OllaM
            model_kwargs: Dict[str, Any] = {}
            if settings.OLLAMA_NUM_CTX: model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
            if settings.OLLAMA_NUM_THREAD: model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
            if settings.OLLAMA_NUM_BATCH: model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
            if settings.OLLAMA_GPU_LAYERS: model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
            if settings.OLLAMA_KEEP_ALIVE: model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

            llm = ChatOllama(
                base_url=settings.OLLAMA_HOST,
                model=local_model_name,
                temperature=0,
                model_kwargs=model_kwargs,
            )
            # Primeiro uso pode exigir carregar o modelo; aumentamos o timeout para reduzir falsos negativos
            if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
                raise RuntimeError(f"Health check falhou para modelo '{local_model_name}'")

            logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
            LLM_ROUTER_COUNTER.labels(role.value, priority.value, local_model_name, "ollama").inc()
            _add_to_pool("ollama", local_model_name, llm)
            return llm
        except Exception as e:
            logger.error(f"Falha crítica ao carregar modelo local para LOCAL_ONLY: {e}", exc_info=True)
            raise RuntimeError(f"Falha crítica ao carregar modelo local. Causa: {e}") from e

    # Provedores de Nuvem (catálogo com factories por modelo)
    cloud_catalog = [
        {
            "name": "Google Gemini", "provider_key": "google_gemini",
            "enabled": _validate_gemini_key(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()),
            "initializer_factory": lambda model: ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                google_api_key=(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)() or None),
            ),
            "models": settings.GEMINI_MODELS if getattr(settings, "GEMINI_MODELS", None) else [
                settings.GEMINI_MODEL_NAME],
        },
        {
            "name": "OpenAI", "provider_key": "openai",
            "enabled": _validate_openai_key(getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()),
            "initializer_factory": lambda model: ChatOpenAI(model=model, temperature=0, client=_get_openai_client()),
            "models": settings.OPENAI_MODELS if getattr(settings, "OPENAI_MODELS", None) else [
                settings.OPENAI_MODEL_NAME],
        },
    ]

    # Estratégia 2: Rápido e Barato ou Alta Qualidade
    if priority in [ModelPriority.FAST_AND_CHEAP, ModelPriority.HIGH_QUALITY]:
        # Seleção adaptativa por modelo considerando orçamento, circuito e métricas observadas
        # Se houver candidatos por papel definidos, usa-os; caso contrário, usa listas de modelos por provedor
        role_key = role.value
        raw_role_candidates = getattr(settings, "LLM_CLOUD_MODEL_CANDIDATES", {}).get(role_key, [])

        # Mapa provider->set(models) derivado de LLM_CLOUD_MODEL_CANDIDATES
        role_candidates_map: Dict[str, set] = {}
        for spec in raw_role_candidates:
            try:
                provider_key, model_name = spec.split(":", 1)
                role_candidates_map.setdefault(provider_key.strip(), set()).add(model_name.strip())
            except Exception:
                logger.warning(f"Spec de candidato inválido: '{spec}' — esperado 'provider:model'")

        candidates = []
        for p in cloud_catalog:
            provider_key = p["provider_key"]
            if exclude_providers and provider_key in exclude_providers:
                continue
            if not (p["enabled"] and _circuit_closed(provider_key) and _budget_allows(provider_key)):
                continue

            # Lista de modelos elegíveis para este papel
            model_list = list(role_candidates_map.get(provider_key, set())) or p["models"]
            for model_name in model_list:
                pricing = _get_model_pricing(provider_key, model_name)
                cost_per_1k = pricing.input_per_1k_usd + pricing.output_per_1k_usd
                stats = _model_stats.get(provider_key, {}).get(model_name, ModelStats())

                candidates.append({
                    "name": p["name"],
                    "provider_key": provider_key,
                    "model_name": model_name,
                    "initializer_factory": p["initializer_factory"],
                    "pricing": pricing,
                    "stats": stats,
                    "cost_per_1k": cost_per_1k,
                })

        if candidates:
            role_key = role.value
            # Filtra por teto de custo estimado por papel (usa EMA dinâmica)
            expected_k = float(_expected_k_ema_by_role.get(role_key, float(
                getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).get(role_key, 2.0))))
            max_cost = float(getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf")))
            filtered = []
            for c in candidates:
                expected_cost = expected_k * c["cost_per_1k"]
                try:
                    LLM_EXPECTED_COST_USD.labels(priority=priority.value, provider=c["provider_key"],
                                                 model=c["model_name"], role=role_key).set(expected_cost)
                except Exception:
                    pass
                if expected_cost <= max_cost:
                    filtered.append(c)
                else:
                    logger.info(
                        f"Candidato filtrado por custo: {c['provider_key']}:{c['model_name']} (expected_cost={expected_cost:.4f} > max_cost={max_cost:.4f}, role={role_key})")

            candidates = filtered or candidates  # se todos foram filtrados, usa originais para evitar vazio
            # Normalizações para scoring
            cost_norm = _normalize([c["cost_per_1k"] for c in candidates])
            latencies = [c["stats"].avg_latency if c["stats"].total_requests > 0 else 1.0 for c in candidates]
            lat_norm = _normalize(latencies)
            success_rates = [c["stats"].success_rate if c["stats"].total_requests > 0 else 0.7 for c in candidates]

            scored = []
            for idx, c in enumerate(candidates):
                econ = getattr(settings, "LLM_ECONOMY_POLICY", "balanced").lower()
                if priority == ModelPriority.FAST_AND_CHEAP:
                    failure_penalty = 1.0 - success_rates[idx]
                    if econ == "strict":
                        w_cost, w_lat, w_fail = 0.75, 0.20, 0.05
                    elif econ == "quality":
                        w_cost, w_lat, w_fail = 0.45, 0.35, 0.20
                    else:  # balanced
                        w_cost, w_lat, w_fail = 0.60, 0.30, 0.10
                    score = w_cost * cost_norm[idx] + w_lat * lat_norm[idx] + w_fail * failure_penalty
                    # Aplica penalização pós-execução acumulada ao score
                    pf = _model_penalty_factors.get(c["provider_key"], {}).get(c["model_name"], 1.0)
                    if pf > 1.0:
                        score = score / pf
                    scored.append((score, c))
                    LLM_SELECTION_SCORE.labels(priority=priority.value, provider=c["provider_key"]).set(score)
                    LLM_MODEL_SELECTION_SCORE.labels(priority=priority.value, provider=c["provider_key"],
                                                     model=c["model_name"]).set(score)
                else:  # HIGH_QUALITY
                    if econ == "strict":
                        alpha = 0.20
                    elif econ == "quality":
                        alpha = 0.00
                    else:  # balanced
                        alpha = 0.10
                    score = success_rates[idx] - 0.3 * lat_norm[idx] - alpha * cost_norm[idx]
                    # Aplica penalização ao score
                    pf = _model_penalty_factors.get(c["provider_key"], {}).get(c["model_name"], 1.0)
                    if pf > 1.0:
                        score = score / pf
                    scored.append((score, c))
                    LLM_SELECTION_SCORE.labels(priority=priority.value, provider=c["provider_key"]).set(score)
                    LLM_MODEL_SELECTION_SCORE.labels(priority=priority.value, provider=c["provider_key"],
                                                     model=c["model_name"]).set(score)

            # Ordenação por score
            if priority == ModelPriority.FAST_AND_CHEAP:
                scored.sort(key=lambda x: x[0])  # menor é melhor
            else:
                scored.sort(key=lambda x: x[0], reverse=True)  # maior é melhor
            # Exploração ocasional: escolhe candidato alternativo
            explore_p = float(getattr(settings, "LLM_EXPLORATION_PERCENT", 0.0) or 0.0)
            if explore_p > 0.0 and len(scored) > 1 and random.random() < explore_p:
                alt_idx = random.randint(1, len(scored) - 1)
                scored[0], scored[alt_idx] = scored[alt_idx], scored[0]
                try:
                    LLM_EXPLORATION_DECISIONS.labels(role=role.value, priority=priority.value).inc()
                except Exception:
                    pass
                logger.info(
                    f"Exploração ativada (p={explore_p:.2f}). Priorizando candidato alternativo index={alt_idx}.")

            for score, cand in scored:
                logger.info(
                    f"Estratégia {priority.value}: Tentando {cand['provider_key']}:{cand['model_name']} (score={score:.3f}, cost_1k={cand['cost_per_1k']:.3f}, avg_lat={cand['stats'].avg_latency:.3f})"
                )
                try:
                    llm = cand["initializer_factory"](cand["model_name"])
                    logger.info(f"LLM '{cand['provider_key']}:{cand['model_name']}' inicializado com sucesso.")
                    LLM_ROUTER_COUNTER.labels(role.value, priority.value, cand["model_name"],
                                              cand["provider_key"]).inc()
                    _add_to_pool(cand["provider_key"], cand["model_name"], llm)
                    return llm
                except Exception as e:
                    logger.warning(
                        f"Falha ao inicializar '{cand['provider_key']}:{cand['model_name']}' (score={score:.3f}): {e}",
                        exc_info=True)

    # Fallback final para o modelo local
    logger.warning("Estratégias de nuvem falharam ou desabilitadas. Recorrendo ao modelo local.")
    try:
        if exclude_providers and "ollama" in exclude_providers:
            raise RuntimeError("Fallback local desativado: 'ollama' está excluído.")
        # Model kwargs para tunar desempenho do OllaM (fallback)
        model_kwargs: Dict[str, Any] = {}
        if settings.OLLAMA_NUM_CTX: model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
        if settings.OLLAMA_NUM_THREAD: model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
        if settings.OLLAMA_NUM_BATCH: model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
        if settings.OLLAMA_GPU_LAYERS: model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
        if settings.OLLAMA_KEEP_ALIVE: model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE

        llm = ChatOllama(
            base_url=settings.OLLAMA_HOST,
            model=local_model_name,
            temperature=0,
            model_kwargs=model_kwargs,
        )
        if not _health_check_ollama(llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3):
            raise RuntimeError(f"Health check falhou para modelo local '{local_model_name}' no fallback")

        LLM_ROUTER_COUNTER.labels(role.value, "fallback", local_model_name, "ollama").inc()
        _add_to_pool("ollama", local_model_name, llm)
        return llm
    except Exception as e:
        logger.critical(f"FALHA CRÍTICA: Nenhum provedor de LLM pôde ser inicializado. Erro final: {e}", exc_info=True)
        raise RuntimeError("Sistema inoperável: nenhum LLM disponível.") from e


# --- Cliente LLM Unificado ---

class LLMClient:
    """Cliente unificado para invocar LLMs com métricas, timeouts e resiliência."""

    def __init__(self, base: BaseChatModel, provider: str, model: str, role: ModelRole, cache_key: str,
                 user_id: Optional[str] = None, project_id: Optional[str] = None):
        self.base = base
        self.provider = provider
        self.model = model
        self.role = role
        self.cache_key = cache_key
        self.user_id = user_id
        self.project_id = project_id

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _validate_prompt(self, prompt: str):
        if not prompt or not prompt.strip():
            raise ValueError("Prompt não pode ser vazio.")
        if len(prompt) > settings.LLM_MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt excede o tamanho máximo de {settings.LLM_MAX_PROMPT_LENGTH} caracteres.")

    def _invoke(self, prompt: str) -> Any:
        return self.base.invoke(prompt)

    def _apply_output_limit(self, max_output_tokens: int):
        try:
            if max_output_tokens and max_output_tokens > 0:
                if self.provider == "openai":
                    mk = getattr(self.base, "model_kwargs", None)
                    if isinstance(mk, dict):
                        mk["max_tokens"] = max_output_tokens
                    else:
                        setattr(self.base, "model_kwargs", {"max_tokens": max_output_tokens})
                elif self.provider == "google_gemini":
                    if hasattr(self.base, "max_output_tokens"):
                        setattr(self.base, "max_output_tokens", max_output_tokens)
                    else:
                        mk = getattr(self.base, "model_kwargs", None)
                        if isinstance(mk, dict):
                            mk["max_output_tokens"] = max_output_tokens
                        else:
                            setattr(self.base, "model_kwargs", {"max_output_tokens": max_output_tokens})
        except Exception:
            # Silencioso: se não conseguir aplicar diretamente, segue sem travar
            pass

    def _compute_output_limit(self, prompt: str) -> int:
        pricing = _get_model_pricing(self.provider, self.model)
        tokens_in = self._estimate_tokens(prompt)
        role_key = self.role.value
        max_req_cost = float(getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(role_key, float("inf")))
        cap = int(getattr(settings, "LLM_MAX_GENERATION_TOKENS_CAP", 0) or 0)
        min_tokens = int(getattr(settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)

        input_cost_usd = (tokens_in / 1000.0) * pricing.input_per_1k_usd
        remaining_req_usd = max(0.0, (max_req_cost - input_cost_usd)) if max_req_cost < float("inf") else float("inf")
        remaining_provider_usd = _budget_remaining(self.provider)
        remaining_user_usd = _tenant_budget_remaining("user", self.user_id)
        remaining_project_usd = _tenant_budget_remaining("project", self.project_id)

        def usd_to_out_tokens(usd: float) -> int:
            if usd == float("inf"):
                return 10 ** 9
            try:
                return int((usd / max(1e-12, pricing.output_per_1k_usd)) * 1000)
            except Exception:
                return 0

        allowances = [
            usd_to_out_tokens(remaining_req_usd),
            usd_to_out_tokens(remaining_provider_usd),
            usd_to_out_tokens(remaining_user_usd),
            usd_to_out_tokens(remaining_project_usd),
        ]

        allowed = min([a for a in allowances if a >= 0]) if allowances else 0
        if cap and cap > 0:
            allowed = min(allowed, cap)
        if allowed < min_tokens and self.provider != "ollama":
            return allowed
        return max(allowed, min_tokens)

    def _sanitize_output(self, text: str) -> str:
        """Aplica sanitização de identidade e remoção de divulgações de modelo.

        - Remove/disfarça trechos como "As an AI/large language model".
        - Substitui nomes de modelos/provedores por "Janus".
        """
        try:
            if not getattr(settings, "IDENTITY_ENFORCEMENT_ENABLED", False):
                return text
            import re
            sanitized = text
            # Remover disclaimers comuns (inglês/português)
            patterns_remove = [
                r"(?i)\bAs an? (?:AI|(?:large )?language model)[^\.\n]*[\.\n]?",
                r"(?i)\bI am an? (?:AI|(?:large )?language model)[^\.\n]*[\.\n]?",
                r"(?i)\bAs a model[^\.\n]*[\.\n]?",
                r"(?i)\bComo (?:um|uma) (?:modelo de linguagem|IA)[^\.\n]*[\.\n]?",
                r"(?i)\bSou (?:um|uma) (?:modelo de linguagem|IA)[^\.\n]*[\.\n]?",
            ]
            for pat in patterns_remove:
                sanitized = re.sub(pat, "", sanitized)

            # Substituir nomes de modelos/provedores por identidade
            identity = getattr(settings, "AGENT_IDENTITY_NAME", None) or getattr(settings, "APP_NAME", "Janus")
            patterns_replace = [
                r"(?i)\bGPT[- ]?\d(?:\.\d)?\b",
                r"(?i)\bChatGPT\b",
                r"(?i)\bClaude(?:[- ]?\d+)?\b",
                r"(?i)\bLlama(?:[- ]?\d+)?\b",
                r"(?i)\bMistral(?:[- ]?\d+)?\b",
                r"(?i)\bGemini\b",
                r"(?i)\bOpenAI\b",
                r"(?i)\bAnthropic\b",
                r"(?i)\bGoogle(?:\s+Gemini)?\b",
                r"(?i)\bCohere\b",
                r"(?i)\bHugging\s*Face\b",
                r"(?i)\bBedrock\b",
            ]
            for pat in patterns_replace:
                sanitized = re.sub(pat, identity, sanitized)

            # Remover rótulos de papel tipo "Assistant:" no início
            sanitized = re.sub(r"(?i)^(assistant|model|ai)\s*:\s*", "", sanitized.strip())
            return sanitized
        except Exception:
            # Em caso de qualquer erro, retorna o texto original
            return text

    async def asend(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM de forma assíncrona."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, prompt, timeout_s)

    def send(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM com resiliência e observabilidade."""
        self._validate_prompt(prompt)

        operation = f"llm_send_{self.provider}"
        base_timeout = timeout_s or settings.LLM_DEFAULT_TIMEOUT_SECONDS
        timeout = get_timeout_recommendation(f"llm_{self.provider}", float(base_timeout))
        circuit_breaker = _provider_circuit_breakers.get(self.provider, _provider_circuit_breakers["unknown"])
        try:
            circuit_breaker.update_params(recovery_timeout=int(max(1, timeout)))
        except Exception:
            pass

        decorated_invoke = resilient(
            max_attempts=settings.LLM_RETRY_MAX_ATTEMPTS,
            initial_backoff=settings.LLM_RETRY_INITIAL_BACKOFF_SECONDS,
            max_backoff=settings.LLM_RETRY_MAX_BACKOFF_SECONDS,
            circuit_breaker=circuit_breaker,
            retry_on=(Exception,),
            operation_name=operation,
        )(self._invoke)

        start = time.perf_counter()
        input_tokens_real: Optional[int] = None
        output_tokens_real: Optional[int] = None
        try:
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "attempt", "").inc()

            # Calcula e aplica limite de geração dinâmico com base em orçamentos/tectos
            allowed_out = self._compute_output_limit(prompt)
            min_tokens = int(getattr(settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)
            if allowed_out < min_tokens and self.provider != "ollama":
                # Fallback para modelo local se não houver orçamento suficiente
                try:
                    model_map = {
                        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
                        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
                        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
                    }
                    local_model_name = model_map.get(self.role, settings.OLLAMA_ORCHESTRATOR_MODEL)
                    model_kwargs: Dict[str, Any] = {}
                    if settings.OLLAMA_NUM_CTX: model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
                    if settings.OLLAMA_NUM_THREAD: model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
                    if settings.OLLAMA_NUM_BATCH: model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
                    if settings.OLLAMA_GPU_LAYERS: model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
                    if settings.OLLAMA_KEEP_ALIVE: model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
                    local_llm = ChatOllama(
                        base_url=settings.OLLAMA_HOST,
                        model=local_model_name,
                        temperature=0,
                        model_kwargs=model_kwargs,
                    )
                    if _health_check_ollama(local_llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 2):
                        logger.info("Sem orçamento suficiente; fallback para modelo local (OllaM).")
                        self.base = local_llm
                        self.provider = "ollama"
                        self.model = local_model_name
                        _add_to_pool("ollama", local_model_name, local_llm)
                    else:
                        logger.warning("Falha no health check do fallback local; mantendo provedor atual.")
                except Exception:
                    logger.warning("Erro ao executar fallback local; mantendo provedor atual.")
            else:
                self._apply_output_limit(allowed_out)

            if timeout > 0:
                future = _get_executor(self.provider).submit(decorated_invoke, prompt)
                result = future.result(timeout=timeout)
            else:
                result = decorated_invoke(prompt)

            elapsed = time.perf_counter() - start
            try:
                record_latency(f"llm_{self.provider}", float(elapsed))
            except Exception:
                pass
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()

            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures = 0
                    break

            output_text = getattr(result, "content", None) or str(result)
            tokens_in = self._estimate_tokens(prompt)
            tokens_out = self._estimate_tokens(output_text)
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "in").inc(tokens_in)
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "out").inc(tokens_out)

            # Atualiza estatísticas e gastos (P4)
            try:
                stats = _provider_stats.get(self.provider)
                if stats:
                    stats.total_requests += 1
                    stats.success_count += 1
                    stats.total_latency_seconds += elapsed
                # Estatísticas por modelo
                _model_stats.setdefault(self.provider, {})
                mstats = _model_stats[self.provider].get(self.model)
                if not mstats:
                    mstats = ModelStats()
                    _model_stats[self.provider][self.model] = mstats
                mstats.total_requests += 1
                mstats.success_count += 1
                mstats.total_latency_seconds += elapsed
                # Precificação por modelo
                pricing = _get_model_pricing(self.provider, self.model)
                cost_usd = (tokens_in / 1000.0) * pricing.input_per_1k_usd + (
                            tokens_out / 1000.0) * pricing.output_per_1k_usd
                _provider_spend_usd[self.provider] = _provider_spend_usd.get(self.provider, 0.0) + max(0.0, cost_usd)
                LLM_PROVIDER_SPEND_USD.labels(self.provider, "request").inc(max(0.0, cost_usd))
                LLM_PROVIDER_BUDGET_REMAINING.labels(self.provider).set(_budget_remaining(self.provider))

                # Atualiza orçamentos de tenant
                _register_tenant_spend("user", self.user_id, cost_usd)
                _register_tenant_spend("project", self.project_id, cost_usd)

                # Atualiza EMA de expected_k por papel
                try:
                    observed_k = (tokens_in + tokens_out) / 1000.0
                    prev = float(_expected_k_ema_by_role.get(self.role.value, float(
                        getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).get(self.role.value, 2.0))))
                    alpha = float(getattr(settings, "LLM_DYNAMIC_EXPECTED_ALPHA", 0.1) or 0.1)
                    new_ema = alpha * observed_k + (1.0 - alpha) * prev
                    _expected_k_ema_by_role[self.role.value] = new_ema
                    LLM_EXPECTED_KTOKENS_GAUGE.labels(role=self.role.value).set(new_ema)
                except Exception:
                    pass

                # Desvio de custo real vs estimativa base (por ktokens)
                try:
                    cost_per_1k = pricing.input_per_1k_usd + pricing.output_per_1k_usd
                    expected_k_baseline = float(_expected_k_ema_by_role.get(self.role.value, 2.0))
                    expected_cost_baseline = expected_k_baseline * cost_per_1k
                    deviation = cost_usd - expected_cost_baseline
                    LLM_COST_DEVIATION_USD.labels(provider=self.provider, model=self.model, role=self.role.value).set(
                        deviation)
                except Exception:
                    pass

                # Penalização se exceder teto por requisição
                try:
                    max_req_cost = float(
                        getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {}).get(self.role.value, float("inf")))
                    if cost_usd > max_req_cost and max_req_cost < float("inf"):
                        inc = float(getattr(settings, "LLM_COST_PENALTY_INCREMENT", 0.25) or 0.25)
                        max_factor = float(getattr(settings, "LLM_COST_PENALTY_MAX_FACTOR", 3.0) or 3.0)
                        curr = _model_penalty_factors.setdefault(self.provider, {}).get(self.model, 1.0)
                        new_pf = min(max_factor, curr + inc)
                        _model_penalty_factors[self.provider][self.model] = new_pf
                        logger.info(
                            f"Penalização aplicada a {self.provider}:{self.model} por exceder custo (pf={new_pf:.2f}).")
                except Exception:
                    pass
            except Exception:
                # Não interrompe fluxo em caso de erro nas métricas
                pass

            return self._sanitize_output(output_text)

        except (ValueError, TimeoutError, CircuitOpenError, FuturesTimeoutError) as e:
            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures += 1
                    break

            elapsed = time.perf_counter() - start
            try:
                record_latency(f"llm_{self.provider}", float(elapsed))
            except Exception:
                pass
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "failure").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "failure", type(e).__name__).inc()

            # Atualiza estatísticas em falha
            try:
                stats = _provider_stats.get(self.provider)
                if stats:
                    stats.total_requests += 1
                    stats.failure_count += 1
                    stats.total_latency_seconds += elapsed
                # Estatísticas por modelo
                _model_stats.setdefault(self.provider, {})
                mstats = _model_stats[self.provider].get(self.model)
                if not mstats:
                    mstats = ModelStats()
                    _model_stats[self.provider][self.model] = mstats
                mstats.total_requests += 1
                mstats.failure_count += 1
                mstats.total_latency_seconds += elapsed
            except Exception:
                pass

            # Penalização de seleção por falha
            try:
                inc = float(getattr(settings, "LLM_FAILURE_PENALTY_INCREMENT", 0.25) or 0.25)
                max_factor = float(getattr(settings, "LLM_FAILURE_PENALTY_MAX_FACTOR", 3.0) or 3.0)
                curr = _model_penalty_factors.setdefault(self.provider, {}).get(self.model, 1.0)
                new_pf = min(max_factor, curr + inc)
                _model_penalty_factors[self.provider][self.model] = new_pf
                logger.info(
                    f"Penalização aplicada a {self.provider}:{self.model} por falha (pf={new_pf:.2f}).")
            except Exception:
                pass

            logger.warning(f"Erro ao enviar prompt para LLM ({type(e).__name__}): {e}")
            if isinstance(e, FuturesTimeoutError):
                raise TimeoutError(f"LLM request timeout after {timeout}s") from e
            raise
        finally:
            pass

    def send_enriched(self, prompt: str, timeout_s: Optional[int] = None) -> Dict[str, Any]:
        """Envia um prompt retornando também tokens reais e custo quando disponível.
        
        Retorno:
        {
            "response": str,
            "provider": str,
            "model": str,
            "role": str,
            "input_tokens": Optional[int],
            "output_tokens": Optional[int],
            "cost_usd": Optional[float],
        }
        """
        self._validate_prompt(prompt)

        operation = f"llm_send_{self.provider}"
        base_timeout = timeout_s or settings.LLM_DEFAULT_TIMEOUT_SECONDS
        timeout = get_timeout_recommendation(f"llm_{self.provider}", float(base_timeout))
        circuit_breaker = _provider_circuit_breakers.get(self.provider, _provider_circuit_breakers["unknown"])
        try:
            circuit_breaker.update_params(recovery_timeout=int(max(1, timeout)))
        except Exception:
            pass

        decorated_invoke = resilient(
            max_attempts=settings.LLM_RETRY_MAX_ATTEMPTS,
            initial_backoff=settings.LLM_RETRY_INITIAL_BACKOFF_SECONDS,
            max_backoff=settings.LLM_RETRY_MAX_BACKOFF_SECONDS,
            circuit_breaker=circuit_breaker,
            retry_on=(Exception,),
            operation_name=operation,
        )(self._invoke)

        start = time.perf_counter()
        input_tokens_real: Optional[int] = None
        output_tokens_real: Optional[int] = None
        try:
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "attempt", "").inc()

            allowed_out = self._compute_output_limit(prompt)
            min_tokens = int(getattr(settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)
            if allowed_out < min_tokens and self.provider != "ollama":
                try:
                    model_map = {
                        ModelRole.ORCHESTRATOR: settings.OLLAMA_ORCHESTRATOR_MODEL,
                        ModelRole.CODE_GENERATOR: settings.OLLAMA_CODER_MODEL,
                        ModelRole.KNOWLEDGE_CURATOR: settings.OLLAMA_CURATOR_MODEL,
                    }
                    local_model_name = model_map.get(self.role, settings.OLLAMA_ORCHESTRATOR_MODEL)
                    model_kwargs: Dict[str, Any] = {}
                    if settings.OLLAMA_NUM_CTX: model_kwargs["num_ctx"] = settings.OLLAMA_NUM_CTX
                    if settings.OLLAMA_NUM_THREAD: model_kwargs["num_thread"] = settings.OLLAMA_NUM_THREAD
                    if settings.OLLAMA_NUM_BATCH: model_kwargs["num_batch"] = settings.OLLAMA_NUM_BATCH
                    if settings.OLLAMA_GPU_LAYERS: model_kwargs["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
                    if settings.OLLAMA_KEEP_ALIVE: model_kwargs["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
                    local_llm = ChatOllama(
                        base_url=settings.OLLAMA_HOST,
                        model=local_model_name,
                        temperature=0,
                        model_kwargs=model_kwargs,
                    )
                    if _health_check_ollama(local_llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 2):
                        logger.info("Sem orçamento suficiente; fallback para modelo local (OllaM).")
                        self.base = local_llm
                        self.provider = "ollama"
                        self.model = local_model_name
                        _add_to_pool("ollama", local_model_name, local_llm)
                    else:
                        logger.warning("Falha no health check do fallback local; mantendo provedor atual.")
                except Exception:
                    logger.warning("Erro ao executar fallback local; mantendo provedor atual.")
            else:
                self._apply_output_limit(allowed_out)

            if timeout > 0:
                future = _get_executor(self.provider).submit(decorated_invoke, prompt)
                result = future.result(timeout=timeout)
            else:
                result = decorated_invoke(prompt)

            elapsed = time.perf_counter() - start
            try:
                record_latency(f"llm_{self.provider}", float(elapsed))
            except Exception:
                pass
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()

            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures = 0
                    break

            output_text = getattr(result, "content", None) or str(result)

            try:
                input_tokens_real, output_tokens_real = self._extract_usage_tokens(result)
            except Exception:
                input_tokens_real = None
                output_tokens_real = None

            tokens_in = input_tokens_real if input_tokens_real is not None else self._estimate_tokens(prompt)
            tokens_out = output_tokens_real if output_tokens_real is not None else self._estimate_tokens(output_text)

            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "in").inc(tokens_in)
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "out").inc(tokens_out)

            cost_usd: Optional[float] = None
            try:
                pricing = _get_model_pricing(self.provider, self.model)
                cost_usd = (tokens_in / 1000.0) * pricing.input_per_1k_usd + (tokens_out / 1000.0) * pricing.output_per_1k_usd
                _provider_spend_usd[self.provider] = _provider_spend_usd.get(self.provider, 0.0) + max(0.0, cost_usd)
                LLM_PROVIDER_SPEND_USD.labels(self.provider, "request").inc(max(0.0, cost_usd))
                LLM_PROVIDER_BUDGET_REMAINING.labels(self.provider).set(_budget_remaining(self.provider))
                _register_tenant_spend("user", self.user_id, cost_usd)
                _register_tenant_spend("project", self.project_id, cost_usd)
            except Exception:
                pass

            enriched = {
                "response": self._sanitize_output(output_text),
                "provider": self.provider,
                "model": self.model,
                "role": self.role.value,
                "input_tokens": input_tokens_real,
                "output_tokens": output_tokens_real,
                "cost_usd": cost_usd,
            }
            return enriched

        except (ValueError, TimeoutError, CircuitOpenError, FuturesTimeoutError) as e:
            key = _pool_key(self.provider, self.model)
            for item in _llm_pool.get(key, []):
                if item.instance is self.base:
                    item.consecutive_failures += 1
                    break
            elapsed = time.perf_counter() - start
            try:
                record_latency(f"llm_{self.provider}", float(elapsed))
            except Exception:
                pass
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "failure").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "failure", type(e).__name__).inc()
            logger.warning(f"Erro ao enviar prompt para LLM ({type(e).__name__}): {e}")
            if isinstance(e, FuturesTimeoutError):
                raise TimeoutError(f"LLM request timeout after {timeout}s") from e
            raise
        finally:
            pass

    def _extract_usage_tokens(self, result: Any) -> (Optional[int], Optional[int]):
        """Tenta extrair tokens reais do objeto de resposta do LangChain.
        Procura campos comuns em usage_metadata/response_metadata.
        """
        try:
            meta_sources = []
            for attr in ("usage_metadata", "response_metadata"):
                if hasattr(result, attr):
                    md = getattr(result, attr)
                    if isinstance(md, dict):
                        meta_sources.append(md)
            # Alguns provedores podem embutir em result.additional_kwargs
            if hasattr(result, "additional_kwargs") and isinstance(getattr(result, "additional_kwargs"), dict):
                ak = getattr(result, "additional_kwargs")
                usage = ak.get("usage") or ak.get("token_usage") or {}
                if isinstance(usage, dict):
                    meta_sources.append(usage)

            in_val: Optional[int] = None
            out_val: Optional[int] = None
            in_keys = ["input_tokens", "prompt_tokens", "input_token_count", "total_tokens_in", "num_prompt_tokens"]
            out_keys = ["output_tokens", "completion_tokens", "output_token_count", "total_tokens_out", "num_completion_tokens"]

            for md in meta_sources:
                for k in in_keys:
                    if md.get(k) is not None:
                        try:
                            in_val = int(md.get(k))
                            break
                        except Exception:
                            pass
                for k in out_keys:
                    if md.get(k) is not None:
                        try:
                            out_val = int(md.get(k))
                            break
                        except Exception:
                            pass
                if in_val is not None or out_val is not None:
                    break

            return in_val, out_val
        except Exception:
            return None, None


# --- Funções de Inferência e Factory ---

def _infer_provider(llm: BaseChatModel) -> str:
    if isinstance(llm, ChatOllama): return "ollama"
    if isinstance(llm, ChatOpenAI): return "openai"
    if isinstance(llm, ChatGoogleGenerativeAI): return "google_gemini"
    return "unknown"


def _infer_model_name(llm: BaseChatModel) -> str:
    for attr in ("model", "model_name"):
        if hasattr(llm, attr):
            return getattr(llm, attr, "unknown")
    return "unknown"


def get_llm_client(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        exclude_providers: Optional[list[str]] = None,
) -> LLMClient:
    """Retorna um cliente unificado, mantendo compatibilidade com get_llm()."""
    cache_key = f"{role.value}_{priority.value}"
    llm = get_llm(role=role, priority=priority, cache_key=cache_key, exclude_providers=exclude_providers)
    provider = _infer_provider(llm)
    model_name = _infer_model_name(llm)
    return LLMClient(llm, provider, model_name, role, cache_key, user_id=user_id, project_id=project_id)
# Pool de executores por provedor
_llm_executors: Dict[str, ThreadPoolExecutor] = {}

def _get_executor(provider_key: str) -> ThreadPoolExecutor:
    max_workers = int(getattr(settings, "LLM_EXECUTOR_MAX_WORKERS", 4) or 4)
    key = provider_key or "default"
    ex = _llm_executors.get(key)
    if ex is None:
        ex = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"llm_{key}")
        _llm_executors[key] = ex
    return ex

_openai_http_client: Optional[httpx.Client] = None
_openai_client: Optional[OpenAI] = None

def _get_openai_client() -> OpenAI:
    global _openai_client, _openai_http_client
    if _openai_client is None:
        max_conn = int(getattr(settings, "OPENAI_HTTP_MAX_CONNECTIONS", 100) or 100)
        max_keep = int(getattr(settings, "OPENAI_HTTP_MAX_KEEPALIVE", 20) or 20)
        timeout = float(getattr(settings, "OPENAI_HTTP_TIMEOUT_SECONDS", settings.LLM_DEFAULT_TIMEOUT_SECONDS) or settings.LLM_DEFAULT_TIMEOUT_SECONDS)
        limits = httpx.Limits(max_connections=max_conn, max_keepalive_connections=max_keep)
        _openai_http_client = httpx.Client(limits=limits, timeout=timeout)
        api_key = getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()
        _openai_client = OpenAI(api_key=api_key, http_client=_openai_http_client)
    return _openai_client
