import logging
import time
from datetime import datetime
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from prometheus_client import Counter, Gauge

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker

from .types import CachedLLM

logger = logging.getLogger(__name__)

# Metrics
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

_llm_pool: dict[str, list[CachedLLM]] = {}
_MAX_CACHE_FAILURES = 3

# Circuit Breakers por provedor para isolar falhas
_provider_circuit_breakers: dict[str, CircuitBreaker] = {
    provider: CircuitBreaker(
        failure_threshold=settings.LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=settings.LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    )
    for provider in ["ollama", "openai", "google_gemini", "unknown"]
}


def _pool_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def _get_from_pool(provider: str, model: str) -> BaseChatModel | None:
    key = _pool_key(provider, model)
    pool = _llm_pool.get(key, [])
    if not pool:
        try:
            LLM_POOL_MISSES.labels(provider, model).inc()
        except Exception:
            pass
        return None
    now = datetime.now()
    ttl = int(
        getattr(settings, "LLM_POOL_TTL_SECONDS", getattr(settings, "LLM_CACHE_TTL_SECONDS", 3600))
        or 3600
    )
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
        pool.append(
            CachedLLM(instance=llm, created_at=datetime.now(), provider=provider, model=model)
        )
        _llm_pool[key] = pool
    else:
        _llm_pool[key] = pool
    try:
        LLM_POOL_SIZE.labels(provider, model).set(len(_llm_pool[key]))
    except Exception:
        pass


def invalidate_cache(provider: str | None = None):
    if provider:
        keys_to_remove = [k for k in list(_llm_pool.keys()) if k.startswith(f"{provider}:")]
        for key in keys_to_remove:
            del _llm_pool[key]
        logger.info(f"Pool invalidado para provider: {provider}")
    else:
        _llm_pool.clear()
        logger.info("Pool de LLMs completamente invalidado.")


def get_llm_pool_snapshot() -> dict[str, list[dict[str, object]]]:
    """Retorna snapshot serializável do pool de LLMs sem expor instâncias internas."""
    snapshot: dict[str, list[dict[str, object]]] = {}
    for key, items in _llm_pool.items():
        snapshot[key] = [
            {
                "provider": item.provider,
                "model": item.model,
                "consecutive_failures": item.consecutive_failures,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
    return snapshot


def get_llm_pool_summary() -> dict[str, int]:
    """Retorna contagem agregada do pool de LLMs."""
    return {
        "pool_keys": len(_llm_pool),
        "pool_total_instances": sum(len(v) for v in _llm_pool.values()),
    }


def get_circuit_breaker_snapshot() -> dict[str, dict[str, Any]]:
    """Retorna snapshot serializável dos circuit breakers por provedor."""
    return {
        provider: {
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "last_failure_time": cb.last_failure_time,
        }
        for provider, cb in _provider_circuit_breakers.items()
    }


def reset_provider_circuit_breaker(provider: str) -> bool:
    """Reseta o circuit breaker do provedor quando existir."""
    cb = _provider_circuit_breakers.get(provider)
    if cb is None:
        return False
    cb.reset()
    return True


def force_reset_stale_open_circuit_breakers(max_open_age_seconds: float) -> list[str]:
    """Reseta CBs OPEN há muito tempo (ou sem timestamp) e retorna provedores resetados."""
    now = time.time()
    reset_providers: list[str] = []
    for provider, cb in _provider_circuit_breakers.items():
        try:
            if cb.state.value != "OPEN":
                continue
            last = float(cb.last_failure_time or 0.0)
            if last == 0.0 or (now - last) > max_open_age_seconds:
                cb.reset()
                reset_providers.append(provider)
        except Exception:
            continue
    return reset_providers


def _circuit_closed(provider: str) -> bool:
    cb = _provider_circuit_breakers.get(provider)
    if not cb:
        return True
    try:
        return not cb.is_open()
    except Exception:
        return True
