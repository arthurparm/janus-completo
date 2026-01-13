import asyncio
import time
import math
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any, Optional

import structlog
from app.config import settings
from app.models.schemas import ScoredExperience
from app.core.memory.security import decrypt_text
from app.core.memory.metrics import (
    memory_short_cache_hits_total,
    memory_short_cache_misses_total,
    memory_short_cache_size,
)

logger = structlog.get_logger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    try:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(dot / (na * nb))
    except Exception:
        return 0.0


class MemoryLocalCache:
    """
    Cache LRU com TTL para experiências de memória.
    Suporta busca por similaridade vetorial nos itens cacheados.
    """

    def __init__(self, ttl_seconds: int = None, max_items: int = None):
        self._ttl = ttl_seconds or int(getattr(settings, "MEMORY_SHORT_TTL_SECONDS", 600))
        self._max_items = max_items or int(getattr(settings, "MEMORY_SHORT_MAX_ITEMS", 512))
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

        # Metrics
        self._metric_hits = memory_short_cache_hits_total
        self._metric_misses = memory_short_cache_misses_total
        self._metric_size = memory_short_cache_size

    async def add(
        self,
        experience_id: str,
        content: str,
        vector: list[float],
        metadata: dict[str, Any],
        ts_ms: int,
    ):
        """Adiciona item ao cache."""
        try:
            async with self._lock:
                now_s = time.time()
                expires_at = now_s + self._ttl

                self._cache[experience_id] = {
                    "id": experience_id,
                    "content": content,  # Content should be encrypted/processed before passing here if needed
                    "metadata": metadata,
                    "type": metadata.get("type"),
                    "vector": vector,
                    "expires_at": expires_at,
                    "ts_ms": ts_ms,
                }
                self._cache.move_to_end(experience_id)

                # Eviction (Capacity)
                while len(self._cache) > self._max_items:
                    self._cache.popitem(last=False)

                self._update_size_metric()
        except Exception:
            logger.debug("Falha ao adicionar item no cache local", exc_info=True)

    async def find_similar(
        self, query_vector: list[float], limit: int = None
    ) -> list[ScoredExperience]:
        """Busca itens similares no cache (linear scan)."""
        results: list[ScoredExperience] = []
        try:
            async with self._lock:
                now_s = time.time()

                # 1. Cleanup Expirados with minimal overhead
                # We iterate copy of keys to safely modify dict
                expired_keys = [
                    k for k, v in self._cache.items() if float(v.get("expires_at", 0)) <= now_s
                ]
                for k in expired_keys:
                    self._cache.pop(k, None)

                if expired_keys:
                    self._update_size_metric()

                # 2. Vector Search
                scan_limit = int(
                    getattr(settings, "MEMORY_SHORT_SCAN_MAX_ITEMS", max(1, self._max_items // 4))
                )

                # Optimized: Iterate efficiently
                # Get last N items (LRU policy keeps most relevant/recent at end usually?)
                # OrderedDict iter gives items in insertion order (oldest first).
                # We might want to check most recent first?
                # The original code did items[-scan_limit:] so it checked the NEWEST items.

                items = list(self._cache.items())
                if scan_limit < len(items):
                    items = items[-scan_limit:]

                for k, v in items:
                    vec = v.get("vector")
                    if not isinstance(vec, list):
                        continue

                    score = cosine_similarity(query_vector, vec)

                    # Construct result
                    results.append(
                        ScoredExperience(
                            id=v.get("id"),
                            content=decrypt_text(v.get("content"), v.get("metadata")),
                            type=v.get("type") or "unknown",
                            timestamp=datetime.now(UTC).isoformat(),  # Approximate
                            metadata=v.get("metadata") or {},
                            score=float(score),
                        )
                    )

                    # Access moves to end (LRU)
                    self._cache.move_to_end(k)

            # Record Hit/Miss (Generic metric, strictly speaking a 'search' isn't simple hit/miss)
            # But the original code did log hits if ANY results were found.
            if results:
                self._metric_hits.inc()
            else:
                self._metric_misses.inc()

        except Exception:
            logger.debug("Falha na busca vetorial do cache local", exc_info=True)

        return results

    def _update_size_metric(self):
        try:
            self._metric_size.set(len(self._cache))
        except Exception:
            pass
