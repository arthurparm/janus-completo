from __future__ import annotations

import time
from typing import Any

import structlog
from qdrant_client import models as qdrant_models

from app.config import settings
from app.core.infrastructure.logging_config import TRACE_ID
from app.db.vector_store import aget_or_create_collection, build_user_secret_collection_name, get_async_qdrant_client
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)


class SecretRetentionService:
    async def purge_expired_batch(self, *, limit: int = 200, active_only: bool = True) -> dict[str, Any]:
        if not bool(getattr(settings, "RETENTION_PURGE_ENABLED", False)):
            return {"status": "skipped", "reason": "retention_purge_disabled"}

        retention_days = max(1, int(getattr(settings, "SECRET_RETENTION_DAYS", 180)))
        cutoff_ms = int((time.time() - (retention_days * 86400)) * 1000)

        collection_name = await aget_or_create_collection(build_user_secret_collection_name())
        client = get_async_qdrant_client()

        must: list[qdrant_models.FieldCondition] = [
            qdrant_models.FieldCondition(
                key="metadata.ts_ms",
                range=qdrant_models.Range(lt=cutoff_ms),
            )
        ]
        if active_only:
            must.append(
                qdrant_models.FieldCondition(
                    key="metadata.active",
                    match=qdrant_models.MatchValue(value=True),
                )
            )
        qfilter = qdrant_models.Filter(must=must)

        points, next_page_offset = await client.scroll(
            collection_name=collection_name,
            scroll_filter=qfilter,
            limit=max(1, int(limit)),
            with_payload=False,
            with_vectors=False,
        )
        point_ids = [getattr(point, "id") for point in (points or []) if getattr(point, "id", None) is not None]
        deleted = 0
        if point_ids:
            await client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.PointIdsList(points=point_ids),
            )
            deleted = len(point_ids)

        try:
            record_audit_event_direct(
                user_id=None,
                endpoint="secret_memory",
                action="secret_retention_purge",
                tool="secret_retention",
                status="success",
                trace_id=TRACE_ID.get(),
                details_json={
                    "collection": collection_name,
                    "cutoff_ms": cutoff_ms,
                    "retention_days": retention_days,
                    "deleted": deleted,
                    "next_offset": str(next_page_offset) if next_page_offset else None,
                },
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "collection": collection_name,
            "retention_days": retention_days,
            "cutoff_ms": cutoff_ms,
            "deleted": deleted,
            "next_offset": next_page_offset,
        }


secret_retention_service = SecretRetentionService()

