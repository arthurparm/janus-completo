import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.config import settings

from .resilience import LLM_POOL_WARMS, _add_to_pool, _get_from_pool, _pool_key

try:
    from langchain_ollama import ChatOllama

    _OLLAMA_AVAILABLE = True
except Exception:
    _OLLAMA_AVAILABLE = False

    class ChatOllama:  # type: ignore[override]
        """Fallback type when langchain_ollama is not installed."""

        pass

logger = logging.getLogger(__name__)

# Pool de executores por provedor
_llm_executors: dict[str, ThreadPoolExecutor] = {}


def _get_executor(provider_key: str) -> ThreadPoolExecutor:
    max_workers = int(getattr(settings, "LLM_EXECUTOR_MAX_WORKERS", 4) or 4)
    key = provider_key or "default"
    ex = _llm_executors.get(key)
    if ex is None:
        ex = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"llm_{key}")
        _llm_executors[key] = ex
    return ex


_openai_http_client: httpx.Client | None = None
_openai_client: OpenAI | None = None


def _get_openai_http_client() -> httpx.Client:
    global _openai_http_client
    if _openai_http_client is None:
        max_conn = int(getattr(settings, "OPENAI_HTTP_MAX_CONNECTIONS", 100) or 100)
        max_keep = int(getattr(settings, "OPENAI_HTTP_MAX_KEEPALIVE", 20) or 20)
        timeout = float(
            getattr(settings, "OPENAI_HTTP_TIMEOUT_SECONDS", settings.LLM_DEFAULT_TIMEOUT_SECONDS)
            or settings.LLM_DEFAULT_TIMEOUT_SECONDS
        )
        limits = httpx.Limits(max_connections=max_conn, max_keepalive_connections=max_keep)

        def _rate_limit_hook(response: httpx.Response):
            try:
                # Verifica headers de rate limit (OpenAI e compatíveis)
                if "x-ratelimit-limit-requests" in response.headers:
                    model = "unknown"
                    try:
                        import json

                        if response.request.content:
                            body = json.loads(response.request.content)
                            model = body.get("model", "unknown")
                    except Exception:
                        pass

                    from .rate_limiter import get_rate_limiter

                    # Detecta provider pela URL ou headers (por enquanto hardcoded openai para headers padrão)
                    provider = "openai"
                    get_rate_limiter().update_limits_from_headers(
                        provider, model, dict(response.headers)
                    )
            except Exception as e:
                logger.warning(f"Erro no hook de rate limit: {e}")

        _openai_http_client = httpx.Client(
            limits=limits, timeout=timeout, event_hooks={"response": [_rate_limit_hook]}
        )
    return _openai_http_client


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        http_client = _get_openai_http_client()
        api_key = getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
        _openai_client = OpenAI(api_key=api_key, http_client=http_client)
    return _openai_client


def _validate_gemini_key(key: str | None) -> bool:
    if not key or not key.startswith("AIza") or len(key) < 30:
        logger.warning("GEMINI_API_KEY parece inválido.")
        return False
    return True


def _validate_openai_key(key: str | None) -> bool:
    if not key or not key.startswith("sk-") or len(key) < 20:
        logger.warning("OPENAI_API_KEY parece inválido.")
        return False
    return True


def _validate_deepseek_key(key: str | None) -> bool:
    if not key or len(key) < 10:
        logger.warning("DEEPSEEK_API_KEY parece inválido.")
        return False
    return True


def _validate_xai_key(key: str | None) -> bool:
    if not key or not key.startswith("xai-") or len(key) < 20:
        logger.warning("XAI_API_KEY parece inválido.")
        return False
    return True


def _validate_openrouter_key(key: str | None) -> bool:
    if not key or not key.startswith("sk-or-") or len(key) < 20:
        logger.warning("OPENROUTER_API_KEY parece inválido.")
        return False
    return True


def _health_check_ollama(llm: ChatOllama, timeout_s: int = 30) -> bool:
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ollama_health")
        model_name = getattr(llm, "model", "unknown")
        logger.debug(
            f"Iniciando health check do Ollama para modelo: {model_name} (timeout={timeout_s}s)"
        )
        future = executor.submit(llm.invoke, "ping")
        future.result(timeout=timeout_s)
        logger.debug("Health check Ollama passou.")
        return True
    except Exception as e:
        logger.error(
            f"Health check Ollama falhou: {e}", exc_info=isinstance(e, FuturesTimeoutError)
        )
        return False
    finally:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)


def create_ollama_llm(
    model_name: str,
    temperature: float | None = None,
    model_kwargs: dict[str, Any] | None = None,
) -> ChatOllama:
    """Creates a configured ChatOllama instance with standard settings."""
    if not _OLLAMA_AVAILABLE:
        raise RuntimeError("langchain_ollama is not installed. Install it to use Ollama models.")

    mk: dict[str, Any] = {}
    if settings.OLLAMA_NUM_CTX:
        mk["num_ctx"] = settings.OLLAMA_NUM_CTX
    if settings.OLLAMA_NUM_THREAD:
        mk["num_thread"] = settings.OLLAMA_NUM_THREAD
    if settings.OLLAMA_NUM_BATCH:
        mk["num_batch"] = settings.OLLAMA_NUM_BATCH
    if settings.OLLAMA_GPU_LAYERS:
        mk["gpu_layer"] = settings.OLLAMA_GPU_LAYERS
    if settings.OLLAMA_KEEP_ALIVE:
        mk["keep_alive"] = settings.OLLAMA_KEEP_ALIVE
    if model_kwargs:
        for key, value in model_kwargs.items():
            if value is not None:
                mk[key] = value

    return ChatOllama(
        base_url=settings.OLLAMA_HOST,
        model=model_name,
        temperature=temperature if temperature is not None else 0,
        model_kwargs=mk,
    )


def warm_llm_pool(specs: list[str] | None = None) -> dict[str, int]:
    warmed: dict[str, int] = {}
    items = specs or list(getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or [])
    for spec in items:
        try:
            provider, model = spec.split(":", 1)
            provider = provider.strip()
            model = model.strip()
            if _get_from_pool(provider, model):
                continue
            if provider == "ollama":
                llm = create_ollama_llm(model)
                if not _health_check_ollama(
                    llm, timeout_s=settings.LLM_DEFAULT_TIMEOUT_SECONDS * 3
                ):
                    continue
                _add_to_pool("ollama", model, llm)
            elif provider == "openai":
                if not _validate_openai_key(
                    getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
                ):
                    continue
                # Ensure client dependencies are initialized
                _get_openai_client()

                llm = ChatOpenAI(
                    model=model,
                    temperature=0,
                    api_key=getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)(),
                    http_client=_openai_http_client,
                )
                _add_to_pool("openai", model, llm)
            elif provider == "google_gemini":
                if not _validate_gemini_key(
                    getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()
                ):
                    continue
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=0,
                    google_api_key=(
                        getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)() or None
                    ),
                )
                _add_to_pool("google_gemini", model, llm)
            elif provider == "deepseek":
                if not _validate_deepseek_key(
                    getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)()
                ):
                    continue
                # Reuse OpenAI client structure but with DeepSeek params
                llm = ChatOpenAI(
                    model=model,
                    temperature=0,
                    api_key=getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)(),
                    base_url=settings.DEEPSEEK_BASE_URL,
                    # Não usamos o http_client compartilhado da OpenAI para evitar conflito de rate limit
                )
                _add_to_pool("deepseek", model, llm)
            elif provider == "openrouter":
                if not _validate_openrouter_key(
                    getattr(settings.OPENROUTER_API_KEY, "get_secret_value", lambda: None)()
                ):
                    continue
                # Reuse OpenAI client structure but with OpenRouter params
                llm = ChatOpenAI(
                    model=model,
                    temperature=0,
                    api_key=getattr(settings.OPENROUTER_API_KEY, "get_secret_value", lambda: None)(),
                    base_url=settings.OPENROUTER_BASE_URL,
                    default_headers={
                        "HTTP-Referer": "https://janus.ai",  # Required by OpenRouter
                        "X-Title": "Janus Agent",  # Optional
                    },
                )
                _add_to_pool("openrouter", model, llm)
            else:
                continue
            key = _pool_key(provider, model)
            warmed[key] = warmed.get(key, 0) + 1
            try:
                LLM_POOL_WARMS.labels(provider, model).inc()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Failed to warm up LLM pool for spec '{spec}': {e}")
    return warmed


def _infer_provider(llm: BaseChatModel) -> str:
    if isinstance(llm, ChatOllama):
        return "ollama"
    if isinstance(llm, ChatOpenAI):
        # Diferencia DeepSeek/xAI/OpenAI/OpenRouter pela URL base
        base_url = str(getattr(llm, "openai_api_base", "") or getattr(llm, "base_url", ""))
        if "deepseek" in base_url.lower():
            return "deepseek"
        if "x.ai" in base_url.lower():
            return "xai"
        if "openrouter" in base_url.lower():
            return "openrouter"
        return "openai"
    if isinstance(llm, ChatGoogleGenerativeAI):
        return "google_gemini"
    return "unknown"


def _infer_model_name(llm: BaseChatModel) -> str:
    for attr in ("model", "model_name"):
        if hasattr(llm, attr):
            return getattr(llm, attr, "unknown")
    return "unknown"
