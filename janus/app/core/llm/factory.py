from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging
import httpx
from openai import OpenAI

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings
from .resilience import _add_to_pool, _get_from_pool, LLM_POOL_WARMS, _pool_key

logger = logging.getLogger(__name__)

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
