import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any

import msgpack

try:
    from prometheus_client import Counter, Gauge
except Exception:
    # Fallback no-op metrics in case Prometheus isn't available
    class _Noop:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

    Counter = Gauge = _Noop

from app.config import settings

# --- Config ---
_DEFAULT_TTL = getattr(settings, "LLM_RESPONSE_CACHE_TTL_SECONDS", 900)
_ENABLED = getattr(settings, "LLM_RESPONSE_CACHE_ENABLED", True)
_CACHE_USE_MSGPACK = getattr(settings, "LLM_RESPONSE_CACHE_USE_MSGPACK", False)
_MAX_ITEMS = int(getattr(settings, "LLM_RESPONSE_CACHE_MAX_ITEMS", 2048))

# --- Metrics ---
_RESPONSE_CACHE_HITS = Counter(
    "llm_response_cache_hits_total", "Total de hits no cache de respostas"
)
_RESPONSE_CACHE_MISSES = Counter(
    "llm_response_cache_misses_total", "Total de misses no cache de respostas"
)
_RESPONSE_CACHE_SIZE = Gauge(
    "llm_response_cache_size", "Tamanho atual do cache de respostas (entradas)"
)
_RESPONSE_CACHE_EVICTIONS = Counter(
    "llm_response_cache_evictions_total", "Total de evictions no cache de respostas"
)
_LLM_CACHE_REQUESTS = Counter("llm_cache_requests_total", "Total de requisições ao cache de LLM")
_LLM_CACHE_HITS = Counter("llm_cache_hits_total", "Total de hits no cache de LLM")

# --- Internal State ---
_lock = threading.RLock()
_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _now() -> float:
    return time.time()


def normalize_prompt(prompt: str) -> str:
    """Normaliza prompt para melhorar hit-rate sem perder semântica."""
    # Remove espaços extras e normaliza quebras de linha
    normalized = " ".join(prompt.strip().split())
    return normalized


def hash_prompt(prompt: str) -> str:
    normalized = normalize_prompt(prompt)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _make_key(prompt_hash: str, role: str, priority: str) -> str:
    return f"{role}:{priority}:{prompt_hash}"


def get(prompt: str, role: str, priority: str) -> dict[str, Any] | None:
    if not _ENABLED:
        return None
    key = _make_key(hash_prompt(prompt), role, priority)
    with _lock:
        _LLM_CACHE_REQUESTS.inc()
        entry = _cache.get(key)
        if not entry:
            _RESPONSE_CACHE_MISSES.inc()
            return None

        # LRU: Mover para o final (mais recente)
        _cache.move_to_end(key)

        ttl = entry.get("ttl", _DEFAULT_TTL)
        if entry["created_at"] + ttl < _now():
            # Expirado; remoção
            _cache.pop(key, None)
            _RESPONSE_CACHE_MISSES.inc()
            _RESPONSE_CACHE_SIZE.set(len(_cache))
            return None

        _RESPONSE_CACHE_HITS.inc()
        _LLM_CACHE_HITS.inc()
        return entry


def put(
    prompt: str,
    role: str,
    priority: str,
    response: str,
    provider: str,
    model: str,
    ttl: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
) -> None:
    if not _ENABLED:
        return
    key = _make_key(hash_prompt(prompt), role, priority)
    with _lock:
        # Se já existe, remove para atualizar e mover pro fim
        if key in _cache:
            _cache.pop(key)

        # Se cheio, remove o mais antigo (primeiro)
        if len(_cache) >= _MAX_ITEMS:
            _cache.popitem(last=False)
            _RESPONSE_CACHE_EVICTIONS.inc()

        entry: dict[str, Any] = {
            "response": response,
            "provider": provider,
            "model": model,
            "role": role,
            "priority": priority,
            "created_at": _now(),
            "ttl": ttl or _DEFAULT_TTL,
            "size_bytes": len(response.encode("utf-8")),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }
        if _CACHE_USE_MSGPACK:
            try:
                entry["response_bin"] = msgpack.packb(response, use_bin_type=True)
                entry["size_bytes"] = len(entry["response_bin"])  # prefer real stored size
                entry["format"] = "msgpack"
            except Exception:
                entry["format"] = "json"
        _cache[key] = entry
        _RESPONSE_CACHE_SIZE.set(len(_cache))


def serialize_entry(entry: dict[str, Any]) -> bytes:
    return msgpack.packb(entry, use_bin_type=True)


def deserialize_entry(data: bytes) -> dict[str, Any]:
    return msgpack.unpackb(data, raw=False)


def invalidate(
    prompt: str | None = None, role: str | None = None, priority: str | None = None
) -> int:
    """Invalida todo cache ou entradas por prompt/role/priority. Retorna o total restante."""
    with _lock:
        if prompt is None and role is None and priority is None:
            _cache.clear()
            _RESPONSE_CACHE_SIZE.set(0)
            return 0
        # Aplica filtros
        to_delete: list[str] = []
        prompt_hash = hash_prompt(prompt) if prompt else None
        for k, v in _cache.items():
            matches = True
            if prompt_hash is not None:
                matches = matches and k.endswith(prompt_hash)
            if role is not None:
                matches = matches and v.get("role") == role
            if priority is not None:
                matches = matches and v.get("priority") == priority
            if matches:
                to_delete.append(k)
        for k in to_delete:
            _cache.pop(k, None)
        _RESPONSE_CACHE_SIZE.set(len(_cache))
        return len(_cache)


def entries() -> list[dict[str, Any]]:
    with _lock:
        return [
            {
                "key": k,
                "provider": v.get("provider"),
                "model": v.get("model"),
                "role": v.get("role"),
                "priority": v.get("priority"),
                "created_at": v.get("created_at"),
                "ttl": v.get("ttl"),
                "size_bytes": v.get("size_bytes"),
                "input_tokens": v.get("input_tokens"),
                "output_tokens": v.get("output_tokens"),
                "cost_usd": v.get("cost_usd"),
            }
            for k, v in _cache.items()
        ]
