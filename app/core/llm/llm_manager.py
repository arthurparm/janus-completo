import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from prometheus_client import Counter, Histogram

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
    """Wrapper para instâncias de LLM com metadados de cache."""
    instance: BaseChatModel
    created_at: datetime
    provider: str
    consecutive_failures: int = 0


_llm_cache: Dict[str, CachedLLM] = {}
_MAX_CACHE_FAILURES = 3  # Limite de falhas para evicção do cache

# Circuit Breakers por provedor para isolar falhas
_provider_circuit_breakers: Dict[str, CircuitBreaker] = {
    provider: CircuitBreaker(
        failure_threshold=settings.LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=settings.LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    )
    for provider in ["ollama", "openai", "google_gemini", "unknown"]
}


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

def _get_from_cache(cache_key: str) -> Optional[CachedLLM]:
    if cache_key not in _llm_cache:
        return None

    cached = _llm_cache[cache_key]
    age = (datetime.now() - cached.created_at).total_seconds()

    if age > settings.LLM_CACHE_TTL_SECONDS or cached.consecutive_failures >= _MAX_CACHE_FAILURES:
        logger.info(
            f"Cache para '{cache_key}' invalidado (age={age:.1f}s, failures={cached.consecutive_failures})."
        )
        del _llm_cache[cache_key]
        return None

    logger.debug(f"Retornando LLM do cache: {cache_key}")
    return cached


def _add_to_cache(cache_key: str, llm: BaseChatModel, provider: str):
    _llm_cache[cache_key] = CachedLLM(
        instance=llm, created_at=datetime.now(), provider=provider
    )
    logger.debug(f"LLM adicionado ao cache: {cache_key}")


def invalidate_cache(provider: Optional[str] = None):
    if provider:
        keys_to_remove = [k for k, v in _llm_cache.items() if v.provider == provider]
        for key in keys_to_remove:
            del _llm_cache[key]
        logger.info(f"Cache invalidado para provider: {provider}")
    else:
        _llm_cache.clear()
        logger.info("Cache de LLMs completamente invalidado.")


# --- Roteador Dinâmico de LLM (get_llm) ---

def get_llm(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY,
        cache_key: str = ""
) -> BaseChatModel:
    """Obtém uma instância de um modelo de linguagem com base no papel e na prioridade."""
    if not cache_key:
        cache_key = f"{role.value}_{priority.value}"

    cached_item = _get_from_cache(cache_key)
    if cached_item:
        return cached_item.instance

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
            llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
            if not _health_check_ollama(llm):
                raise RuntimeError(f"Health check falhou para modelo '{local_model_name}'")

            logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
            LLM_ROUTER_COUNTER.labels(role.value, priority.value, local_model_name, "ollama").inc()
            _add_to_cache(cache_key, llm, "ollama")
            return llm
        except Exception as e:
            logger.error(f"Falha crítica ao carregar modelo local para LOCAL_ONLY: {e}", exc_info=True)
            raise RuntimeError(f"Falha crítica ao carregar modelo local. Causa: {e}") from e

    # Provedores de Nuvem (ordenados por prioridade/custo)
    cloud_providers = [
        {
            "name": "Google Gemini", "provider_key": "google_gemini",
            "enabled": _validate_gemini_key(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()),
            "initializer": lambda: ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL_NAME, temperature=0,
                                                          google_api_key=(getattr(settings.GEMINI_API_KEY,
                                                                                  'get_secret_value',
                                                                                  lambda: None)() or None)),
            "model_name": settings.GEMINI_MODEL_NAME,
        },
        {
            "name": "OpenAI", "provider_key": "openai",
            "enabled": _validate_openai_key(getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()),
            "initializer": lambda: ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0),
            "model_name": settings.OPENAI_MODEL_NAME,
        }
    ]

    # Estratégia 2: Rápido e Barato ou Alta Qualidade
    if priority in [ModelPriority.FAST_AND_CHEAP, ModelPriority.HIGH_QUALITY]:
        for provider in cloud_providers:
            if provider["enabled"]:
                logger.info(f"Estratégia {priority.value}: Tentando o provedor: {provider['name']}")
                try:
                    llm = provider["initializer"]()
                    logger.info(f"LLM do provedor '{provider['name']}' inicializado com sucesso.")
                    LLM_ROUTER_COUNTER.labels(role.value, priority.value, provider["model_name"],
                                              provider["provider_key"]).inc()
                    _add_to_cache(cache_key, llm, provider["provider_key"])
                    return llm
                except Exception as e:
                    logger.warning(f"Falha ao inicializar o provedor '{provider['name']}': {e}.", exc_info=True)

    # Fallback final para o modelo local
    logger.warning("Estratégias de nuvem falharam ou desabilitadas. Recorrendo ao modelo local.")
    try:
        llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
        if not _health_check_ollama(llm):
            raise RuntimeError(f"Health check falhou para modelo local '{local_model_name}' no fallback")

        LLM_ROUTER_COUNTER.labels(role.value, "fallback", local_model_name, "ollama").inc()
        _add_to_cache(cache_key, llm, "ollama")
        return llm
    except Exception as e:
        logger.critical(f"FALHA CRÍTICA: Nenhum provedor de LLM pôde ser inicializado. Erro final: {e}", exc_info=True)
        raise RuntimeError("Sistema inoperável: nenhum LLM disponível.") from e


# --- Cliente LLM Unificado ---

class LLMClient:
    """Cliente unificado para invocar LLMs com métricas, timeouts e resiliência."""

    def __init__(self, base: BaseChatModel, provider: str, model: str, role: ModelRole, cache_key: str):
        self.base = base
        self.provider = provider
        self.model = model
        self.role = role
        self.cache_key = cache_key

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _validate_prompt(self, prompt: str):
        if not prompt or not prompt.strip():
            raise ValueError("Prompt não pode ser vazio.")
        if len(prompt) > settings.LLM_MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt excede o tamanho máximo de {settings.LLM_MAX_PROMPT_LENGTH} caracteres.")

    def _invoke(self, prompt: str) -> Any:
        return self.base.invoke(prompt)

    async def asend(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM de forma assíncrona."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, prompt, timeout_s)

    def send(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """Envia um prompt para o LLM com resiliência e observabilidade."""
        self._validate_prompt(prompt)

        operation = f"llm_send_{self.provider}"
        timeout = timeout_s or settings.LLM_DEFAULT_TIMEOUT_SECONDS
        circuit_breaker = _provider_circuit_breakers.get(self.provider, _provider_circuit_breakers["unknown"])

        decorated_invoke = resilient(
            max_attempts=settings.LLM_RETRY_MAX_ATTEMPTS,
            initial_backoff=settings.LLM_RETRY_INITIAL_BACKOFF_SECONDS,
            max_backoff=settings.LLM_RETRY_MAX_BACKOFF_SECONDS,
            circuit_breaker=circuit_breaker,
            retry_on=(Exception,),
            operation_name=operation,
        )(self._invoke)

        start = time.perf_counter()
        executor = None
        try:
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "attempt", "").inc()

            if timeout > 0:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"llm_{self.provider}")
                future = executor.submit(decorated_invoke, prompt)
                result = future.result(timeout=timeout)
            else:
                result = decorated_invoke(prompt)

            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()

            # Sucesso: reseta o contador de falhas do cache
            if self.cache_key in _llm_cache:
                _llm_cache[self.cache_key].consecutive_failures = 0

            output_text = getattr(result, "content", None) or str(result)
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "in").inc(self._estimate_tokens(prompt))
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "out").inc(self._estimate_tokens(output_text))

            return output_text

        except (ValueError, TimeoutError, CircuitOpenError, FuturesTimeoutError) as e:
            # Falha: incrementa o contador de falhas e propaga o erro
            if self.cache_key in _llm_cache:
                _llm_cache[self.cache_key].consecutive_failures += 1

            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "failure").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "failure", type(e).__name__).inc()

            logger.warning(f"Erro ao enviar prompt para LLM ({type(e).__name__}): {e}")
            if isinstance(e, FuturesTimeoutError):
                raise TimeoutError(f"LLM request timeout after {timeout}s") from e
            raise
        finally:
            if executor:
                executor.shutdown(wait=False, cancel_futures=True)


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
        priority: ModelPriority = ModelPriority.LOCAL_ONLY
) -> LLMClient:
    """Retorna um cliente unificado, mantendo compatibilidade com get_llm()."""
    cache_key = f"{role.value}_{priority.value}"
    llm = get_llm(role=role, priority=priority, cache_key=cache_key)
    provider = _infer_provider(llm)
    model_name = _infer_model_name(llm)
    return LLMClient(llm, provider, model_name, role, cache_key)
