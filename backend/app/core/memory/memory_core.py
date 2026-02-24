import asyncio
import time
import uuid
from typing import Any
from datetime import UTC, datetime

import structlog
from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.core.embeddings.embedding_manager import aembed_text
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.core.infrastructure.resilience import CircuitBreaker
from app.core.memory.metrics import (
    memory_operations_total,
    memory_quota_rejections_total,
)
from app.core.memory.security import redact_pii, encrypt_text, decrypt_text
from app.core.memory.local_cache import MemoryLocalCache
from app.core.memory.providers.qdrant_provider import QdrantProvider
from app.models.schemas import Experience, ScoredExperience

logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Núcleo de Memória Refatorado.
    Orquestra Operações entre Cache Local, Vector Store (Qdrant) e Segurança.
    """

    def __init__(
        self,
        client: AsyncQdrantClient | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        config: Any = None,
    ):
        self.settings = config if config is not None else settings

        # Components
        if client is None:
            client = AsyncQdrantClient(
                host=self.settings.QDRANT_HOST, port=self.settings.QDRANT_PORT
            )
        self.provider = QdrantProvider(client=client, circuit_breaker=circuit_breaker)
        self.cache = MemoryLocalCache()
        self.collection_name = self.provider.collection_name
        self._cb = self.provider._cb

        # Quota Config
        self._quota: dict[str, dict[str, Any]] = {}
        self._quota_window_s = int(getattr(self.settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        self._quota_max_items = int(
            getattr(self.settings, "MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN", 200)
        )
        self._quota_max_bytes = int(
            getattr(self.settings, "MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN", 5_000_000)
        )

        # Metrics
        self._quota_rejections = memory_quota_rejections_total
        self._ops_total = memory_operations_total

    async def initialize(self):
        """Inicializa provedores."""
        await self.provider.initialize()

    async def close(self):
        """Fecha recursos."""
        await self.provider.close()

    async def _try_revive_connection(self) -> bool:
        """Tentativa de reviver conexão (wrapper)."""
        return await self.provider.try_revive()

    async def amemorize(self, experience: Experience):
        """
        Adiciona uma experiência à memória (Fluxo Completo).
        """
        # 1. Validation & Quotas
        self._check_content_size(experience.content)
        self._check_quota(experience)

        # 2. PII & Security
        final_content = experience.content
        pii_types = []
        if getattr(self.settings, "MEMORY_PII_REDACT", True) and isinstance(final_content, str):
            final_content, pii_types = redact_pii(final_content)

        # 3. Embedding (on redacted content)
        try:
            vector = await aembed_text(str(final_content))
        except Exception:
            logger.warning("Embedding failed, using zero vector")
            vector = [0.0] * self.provider._vector_size  # Access internal size? or get from config

        # 4. Encryption
        encrypted_content, enc_method = encrypt_text(str(final_content))

        # 5. Prepare Payload
        ts_ms = self._get_timestamp_ms(experience.timestamp)
        payload = experience.dict()
        payload.update(
            {
                "ts_ms": ts_ms,
                "content": encrypted_content,
                "metadata": payload.get("metadata", {}) or {},
            }
        )

        meta = payload["metadata"]
        if enc_method:
            meta["enc"] = enc_method
        if pii_types:
            meta["pii"] = pii_types
            meta["pii_redacted"] = True

        # Preserve type for filtering
        if payload.get("type"):
            meta["type"] = payload["type"]

        # 6. Upsert (Provider + Cache)
        clean_id = self._ensure_valid_point_id(experience.id)

        await self.provider.upsert(clean_id, vector, payload)

        await self.cache.add(
            experience_id=str(experience.id),
            content=encrypted_content,
            vector=vector,
            metadata=meta,
            ts_ms=ts_ms,
        )

        # 7. Update Quotas
        self._update_quota(experience)
        self._ops_total.labels(operation="memorize").inc()

    async def arecall(
        self, query: str, limit: int | None = 10, min_score: float | None = None
    ) -> list[ScoredExperience]:
        """Busca combinada (Cache + Vector DB)."""
        limit = limit or 10

        # 1. Embed Query
        query_vector = await self._safe_embed(query)

        # 2. Parallel Search
        cache_task = self.cache.find_similar(query_vector, limit)
        provider_task = self.provider.search(query_vector, limit)

        cache_results, provider_points = await asyncio.gather(cache_task, provider_task)

        # 3. Map Provider Results
        db_results = [self._point_to_experience(p) for p in provider_points]

        # 4. Merge & Deduplicate
        return self._merge_results(cache_results + db_results, limit, min_score)

    async def arecall_filtered(
        self,
        query: str | None,
        filters: dict[str, Any],
        limit: int | None = 10,
        min_score: float | None = None,
    ):
        """Busca com filtros."""
        limit = limit or 10
        query_vector = await self._safe_embed(query) if query else [0.0] * 1536
        qfilter = self._build_filter(filters)

        points = await self.provider.search(
            query_vector, limit, query_filter=qfilter, operation_name="qdrant_search_filtered"
        )

        results = [self._point_to_experience(p) for p in points]
        return self._filter_score_limit(results, min_score, limit)

    async def arecall_by_timeframe(
        self,
        query: str | None,
        start_ts_ms: int | None,
        end_ts_ms: int | None,
        limit: int = 10,
        min_score: float = None,
    ):
        """Busca por janela temporal."""
        limit = limit or 10
        query_vector = await self._safe_embed(query) if query else [0.0] * 1536

        rng = models.Range(gte=start_ts_ms, lte=end_ts_ms)
        qfilter = models.Filter(must=[models.FieldCondition(key="ts_ms", range=rng)])

        points = await self.provider.search(
            query_vector, limit, query_filter=qfilter, operation_name="qdrant_search_timeframe"
        )

        results = [self._point_to_experience(p) for p in points]
        # Pós-filtro (garantia extra)
        results = [
            r for r in results if self._is_within(r.metadata.get("ts_ms"), start_ts_ms, end_ts_ms)
        ]
        return self._filter_score_limit(results, min_score, limit)

    async def arecall_recent_failures(
        self, limit: int = 10, timeframe_seconds: int = 3600, min_score: float = None
    ):
        """Busca falhas recentes."""
        # Using scroll logic from provider
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        # Defensive null-safety: default to 1 hour if None
        safe_timeframe = timeframe_seconds if timeframe_seconds is not None else 3600
        start_ms = now_ms - (safe_timeframe * 1000)

        qfilter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.status", match=models.MatchValue(value="failure")
                ),
                models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
            ]
        )

        points = await self.provider.scroll(qfilter, limit)
        results = [self._point_to_experience(p) for p in points]
        return self._filter_score_limit(results, min_score, limit)

    async def arecall_recent_lessons(
        self, limit: int = 10, timeframe_seconds: int = 3600, min_score: float = None
    ):
        """Busca lições recentes."""
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        # Defensive null-safety: default to 1 hour if None
        safe_timeframe = timeframe_seconds if timeframe_seconds is not None else 3600
        start_ms = now_ms - (safe_timeframe * 1000)

        qfilter = models.Filter(
            must=[
                models.FieldCondition(key="type", match=models.MatchValue(value="lessons_learned")),
                models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
            ]
        )

        points = await self.provider.scroll(qfilter, limit)
        results = [self._point_to_experience(p) for p in points]
        return self._filter_score_limit(results, min_score, limit)

    # --- Helpers ---

    def reset_circuit_breaker(self):
        if self.provider.circuit_breaker:
            self.provider.circuit_breaker.reset()
            self.provider._offline = False

    def health_check(self) -> bool:
        # Simplified health check delegating to circuit breaker state mainly
        return not self.provider.is_offline

    def get_circuit_breaker_status(self):
        # Delegate basic stats
        cb = self.provider.circuit_breaker
        return {
            "offline": self.provider.is_offline,
            "circuit_breaker_open": cb.is_open(),
            "metrics": cb.get_health_status() if hasattr(cb, "get_health_status") else {},
        }

    async def _safe_embed(self, text: str) -> list[float]:
        try:
            return await aembed_text(text)
        except Exception:
            return [0.0] * 1536

    def _check_content_size(self, content):
        max_chars = int(getattr(self.settings, "MEMORY_MAX_CONTENT_CHARS", 20000))
        if isinstance(content, str) and len(content) > max_chars:
            raise ValueError(f"Content exceeds {max_chars} chars")

    def _check_quota(self, experience):
        if self._quota_max_items <= 0 and self._quota_max_bytes <= 0:
            return

        metadata = experience.metadata or {}
        origin = str(metadata.get("origin") or "unknown")
        now = time.time()
        entry = self._quota.get(origin)
        if entry is None or now - float(entry.get("window_start", 0.0)) >= self._quota_window_s:
            entry = {"window_start": now, "items": 0, "bytes": 0}
            self._quota[origin] = entry

        content_bytes = len(str(experience.content or "").encode("utf-8"))
        projected_items = int(entry.get("items", 0)) + 1
        projected_bytes = int(entry.get("bytes", 0)) + content_bytes

        if self._quota_max_items > 0 and projected_items > self._quota_max_items:
            self._quota_rejections.inc()
            raise ValueError(
                f"Memory item quota exceeded for origin '{origin}' "
                f"({projected_items}/{self._quota_max_items})"
            )

        if self._quota_max_bytes > 0 and projected_bytes > self._quota_max_bytes:
            self._quota_rejections.inc()
            raise ValueError(
                f"Memory byte quota exceeded for origin '{origin}' "
                f"({projected_bytes}/{self._quota_max_bytes})"
            )

    def _update_quota(self, experience):
        if self._quota_max_items <= 0 and self._quota_max_bytes <= 0:
            return

        metadata = experience.metadata or {}
        origin = str(metadata.get("origin") or "unknown")
        now = time.time()
        entry = self._quota.get(origin)
        if entry is None or now - float(entry.get("window_start", 0.0)) >= self._quota_window_s:
            entry = {"window_start": now, "items": 0, "bytes": 0}
            self._quota[origin] = entry

        content_bytes = len(str(experience.content or "").encode("utf-8"))
        entry["items"] = int(entry.get("items", 0)) + 1
        entry["bytes"] = int(entry.get("bytes", 0)) + content_bytes

        # Best-effort cleanup to avoid unbounded growth of stale origins.
        if len(self._quota) > 2048:
            cutoff = now - (self._quota_window_s * 2)
            for bucket_origin, bucket in list(self._quota.items()):
                if float(bucket.get("window_start", 0.0)) < cutoff:
                    self._quota.pop(bucket_origin, None)

    def _get_timestamp_ms(self, ts_str):
        try:
            return int(datetime.fromisoformat(ts_str).timestamp() * 1000)
        except:
            return int(datetime.now(UTC).timestamp() * 1000)

    def _ensure_valid_point_id(self, id_val):
        # Reuse logic or import from util
        try:
            return int(id_val)
        except:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(id_val)))

    def _build_filter(self, filters: dict[str, Any]) -> models.Filter | None:
        if not filters:
            return None
        must = []
        for k, v in filters.items():
            key = f"metadata.{k}" if k in ("origin", "status") else k
            must.append(models.FieldCondition(key=key, match=models.MatchValue(value=v)))
        return models.Filter(must=must) if must else None

    def _point_to_experience(self, point) -> ScoredExperience:
        payload = point.payload or {}
        return ScoredExperience(
            id=str(point.id),
            content=decrypt_text(payload.get("content"), payload.get("metadata")),
            type=payload.get("type") or "episodic",
            timestamp=payload.get("timestamp") or datetime.now(UTC).isoformat(),
            metadata=payload.get("metadata") or {},
            score=point.score if hasattr(point, "score") else 0.0,
        )

    def _merge_results(self, all_results, limit, min_score):
        combined = {}
        for r in all_results:
            if not combined.get(r.id) or (r.score > combined[r.id].score):
                combined[r.id] = r

        sorted_res = sorted(combined.values(), key=lambda x: x.score or 0.0, reverse=True)
        if min_score:
            sorted_res = [r for r in sorted_res if (r.score or 0.0) >= min_score]
        return sorted_res[:limit]

    def _is_within(self, ts, start, end):
        if ts is None:
            return True
        if start and ts < start:
            return False
        if end and ts > end:
            return False
        return True

    def _filter_score_limit(self, results, min_score, limit):
        # Helper
        if min_score:
            results = [r for r in results if (r.score or 0.0) >= min_score]
        return results[:limit]


# --- Global Instance ---
_memory_db_instance: MemoryCore | None = None


async def initialize_memory_db():
    global _memory_db_instance
    if _memory_db_instance is None:
        _memory_db_instance = MemoryCore()
        await _memory_db_instance.initialize()


async def get_memory_db() -> MemoryCore:
    if _memory_db_instance is None:
        await initialize_memory_db()
    return _memory_db_instance


async def close_memory_db():
    global _memory_db_instance
    if _memory_db_instance:
        await _memory_db_instance.close()
        _memory_db_instance = None
