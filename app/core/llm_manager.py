import logging
import time
from enum import Enum
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.resilience import resilient, CircuitBreaker

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
    ["provider", "model", "role", "direction"],  # direction in|out
)

logger = logging.getLogger(__name__)

# Cache para as instâncias de LLM
_llm_instances: Dict[str, BaseChatModel] = {}

_DEFAULT_TIMEOUT_S = getattr(settings, "LLM_TIMEOUT_SECONDS", 60)
_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


class ModelRole(Enum):
    """Define os papéis cognitivos para seleção do modelo apropriado."""
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"


class ModelPriority(Enum):
    """Define a prioridade para o roteador de modelos, balanceando custo e performance."""
    LOCAL_ONLY = "local_only"  # Força o uso do cérebro soberano local (Ollama)
    FAST_AND_CHEAP = "fast_and_cheap"  # Prioriza APIs de nuvem de baixo custo para tarefas rápidas
    HIGH_QUALITY = "high_quality"  # Prioriza os modelos de nuvem mais poderosos (e caros)


def get_llm(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY
) -> BaseChatModel:
    """
    Obtém uma instância de um modelo de linguagem com base no papel e na prioridade,
    atuando como um roteador dinâmico de modelos.
    """
    cache_key = f"{role.value}_{priority.value}"
    if cache_key in _llm_instances:
        logger.debug(f"Retornando instância de LLM em cache para: {cache_key}")
        return _llm_instances[cache_key]

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
            logger.info(f"Estratégia LOCAL_ONLY: Tentando inicializar o modelo '{local_model_name}'...")
            llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
            llm.invoke("Confirme sua funcionalidade.")
            logger.info(f"Modelo local '{local_model_name}' inicializado com sucesso.")
            LLM_ROUTER_COUNTER.labels(role=role.value, priority=priority.value, model_name=local_model_name,
                                      provider="ollama").inc()
            _llm_instances[cache_key] = llm
            return llm
        except Exception as e:
            logger.warning(
                f"Falha ao inicializar o modelo local '{local_model_name}': {e}. Nenhuma outra estratégia será tentada para LOCAL_ONLY.")
            raise RuntimeError(f"Falha crítica ao tentar carregar o modelo local com prioridade LOCAL_ONLY.")

    # Provedores de Nuvem (ordenados por prioridade/custo)
    cloud_providers = [
        {
            "name": "Google Gemini",  # Frequentemente oferece um bom equilíbrio de custo/performance
            "enabled": getattr(settings, "GEMINI_API_KEY", None) and settings.GEMINI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL_NAME, temperature=0,
                                                          google_api_key=settings.GEMINI_API_KEY.get_secret_value())
        },
        {
            "name": "OpenAI",
            "enabled": getattr(settings, "OPENAI_API_KEY", None) and settings.OPENAI_API_KEY.get_secret_value(),
            "initializer": lambda: ChatOpenAI(model=settings.OPENAI_MODEL_NAME, temperature=0,
                                              api_key=settings.OPENAI_API_KEY.get_secret_value())
        }
    ]

    # Estratégia 2: Rápido e Barato (tentamos provedores de nuvem)
    if priority == ModelPriority.FAST_AND_CHEAP or priority == ModelPriority.HIGH_QUALITY:
        # A ordem em cloud_providers pode ser ajustada para refletir qual é o mais "barato"
        for provider in cloud_providers:
            if provider["enabled"]:
                logger.info(f"Estratégia {priority.value}: Tentando o provedor de nuvem: {provider['name']}")
                try:
                    llm = provider["initializer"]()
                    logger.info(f"LLM do provedor '{provider['name']}' inicializado com sucesso.")
                    model_name = settings.GEMINI_MODEL_NAME if provider[
                                                                   'name'] == 'Google Gemini' else settings.OPENAI_MODEL_NAME
                    LLM_ROUTER_COUNTER.labels(role=role.value, priority=priority.value, model_name=model_name,
                                              provider=provider['name'].lower()).inc()
                    _llm_instances[cache_key] = llm
                    return llm
                except Exception as e:
                    logger.warning(f"Falha ao inicializar o provedor '{provider['name']}': {e}.")

    # Fallback final para o modelo local se as estratégias de nuvem falharem
    logger.warning(f"Todas as estratégias de nuvem falharam. Recorrendo ao modelo local como fallback final.")
    try:
        llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=local_model_name, temperature=0)
        llm.invoke("Confirme sua funcionalidade.")
        LLM_ROUTER_COUNTER.labels(role=role.value, priority="fallback", model_name=local_model_name,
                                  provider="ollama").inc()
        _llm_instances[cache_key] = llm
        return llm
    except Exception as e:
        raise RuntimeError(
            f"FALHA CRÍTICA: Nenhum provedor de LLM (nem nuvem, nem local) pôde ser inicializado. Erro final: {e}"
        )


class LLMClient:
    """Cliente unificado para invocar LLMs com métricas, timeouts e resiliência."""

    def __init__(self, base: BaseChatModel, provider: str, model: str, role: "ModelRole"):
        self.base = base
        self.provider = provider
        self.model = model
        self.role = role

    def _estimate_tokens(self, text: str) -> int:
        # Aproximação simples
        return max(1, len(text) // 4)

    def _invoke(self, prompt: str) -> Any:
        # Chamada direta; LangChain lida com serialização
        return self.base.invoke(prompt)

    def send(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        operation = f"llm_send_{self.provider}"
        timeout = timeout_s or _DEFAULT_TIMEOUT_S

        # Wrapper para aplicar decorador por chamada (com CB + retry exponencial)
        decorated = resilient(
            max_attempts=3,
            initial_backoff=0.5,
            max_backoff=5.0,
            circuit_breaker=_CB,
            retry_on=(Exception,),
            operation_name=operation,
        )(self._invoke)

        start = time.perf_counter()
        try:
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "attempt", "").inc()

            # Aplica timeout efetivo usando ThreadPoolExecutor
            if timeout and timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(decorated, prompt)
                    try:
                        result = future.result(timeout=timeout)
                    except FuturesTimeoutError:
                        future.cancel()
                        raise TimeoutError(f"LLM request timeout after {timeout}s")
            else:
                result = decorated(prompt)

            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "success").observe(elapsed)

            # Extrai texto
            output_text = None
            try:
                # langchain returns BaseMessage or str depending on backend
                output_text = getattr(result, "content", None) or str(result)
            except Exception:
                output_text = str(result)

            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "success", "").inc()
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "in").inc(self._estimate_tokens(prompt))
            LLM_TOKENS.labels(self.provider, self.model, self.role.value, "out").inc(self._estimate_tokens(output_text))
            return output_text
        except Exception as e:
            elapsed = time.perf_counter() - start
            LLM_LATENCY.labels(self.provider, self.model, self.role.value, "failure").observe(elapsed)
            LLM_REQUESTS.labels(self.provider, self.model, self.role.value, "failure", type(e).__name__).inc()
            raise

    def health_check(self) -> bool:
        try:
            _ = self.send("ping", timeout_s=10)
            return True
        except Exception:
            return False


def _infer_provider(llm: BaseChatModel) -> str:
    if isinstance(llm, ChatOllama):
        return "ollama"
    if isinstance(llm, ChatOpenAI):
        return "openai"
    if isinstance(llm, ChatGoogleGenerativeAI):
        return "google_gemini"
    return "unknown"


def _infer_model_name(llm: BaseChatModel) -> str:
    for attr in ("model", "model_name", "model_id"):
        if hasattr(llm, attr):
            try:
                val = getattr(llm, attr)
                if isinstance(val, str):
                    return val
            except Exception:
                pass
    return "unknown"


def get_llm_client(role: ModelRole = ModelRole.ORCHESTRATOR, priority: ModelPriority = ModelPriority.LOCAL_ONLY) -> LLMClient:
    """Retorna um cliente unificado, mantendo compatibilidade com get_llm()."""
    llm = get_llm(role=role, priority=priority)
    provider = _infer_provider(llm)
    model_name = _infer_model_name(llm)
    return LLMClient(llm, provider, model_name, role)
