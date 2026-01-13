import hashlib
import re
from typing import Any
from uuid import uuid4

import structlog
from qdrant_client import models

from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client
from app.repositories.observability_repository import record_audit_event_direct
from app.core.exceptions.document_exceptions import QuotaExceededError
from app.core.monitoring.document_metrics import get_metrics_recorder
from app.services.document_parser_service import DocumentParserService

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None

from app.core.embeddings.embedding_manager import aembed_texts

logger = structlog.get_logger(__name__)


class DocumentIngestionService:
    def __init__(self, memory_service):
        self._memory_service = memory_service
        self._parser = DocumentParserService()
        self._metrics = get_metrics_recorder()

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
        if not text:
            return []
        chunks: list[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= n:
                break
            start = end - overlap
            start = max(start, 0)
        return chunks

    async def ingest_file(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        doc_id = f"doc:{user_id}:{uuid4().hex}"
        span_cm = _tracer.start_as_current_span("doc.ingest") if _OTEL else nullcontext()

        with span_cm as span:
            if _OTEL and span is not None:
                try:
                    tid = TRACE_ID.get()
                    sid = USER_ID.get()
                    if tid and tid != "-":
                        span.set_attribute("janus.trace_id", tid)
                    if sid and sid != "-":
                        span.set_attribute("janus.user_id", sid)
                    span.set_attribute("doc.filename", filename)
                    span.set_attribute("doc.content_type", (content_type or "").lower())
                except Exception as e:
                    logger.debug("otel_span_attribute_failed", error=str(e))

        # Parse document using DocumentParserService
        text = self._parser.parse(data, content_type, filename)

        if not text:
            logger.warning(
                "document_text_extraction_empty",
                filename=filename,
                content_type=content_type,
            )
            return {"doc_id": doc_id, "chunks": 0, "status": "unsupported_content_type"}

        # Chunk text
        chunk_size = 1000
        overlap = 100
        try:
            from app.config import settings

            chunk_size = int(getattr(settings, "DOC_CHUNK_SIZE", 1000) or 1000)
            overlap = int(getattr(settings, "DOC_CHUNK_OVERLAP", 100) or 100)
        except Exception as e:
            logger.debug("config_loading_failed", error=str(e))

        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        # Record chunk metrics
        self._metrics.record_chunks_count(len(chunks))
        if _OTEL and span is not None:
            try:
                span.set_attribute("doc.chunk_count", len(chunks))
            except Exception as e:
                logger.debug("otel_chunk_count_failed", error=str(e))

        # Handle empty document
        if not chunks:
            self._metrics.record_ingest_status("empty", user_id)
            try:
                record_audit_event_direct(
                    {
                        "user_id": int(user_id) if user_id is not None else None,
                        "endpoint": "doc:ingest",
                        "action": "ingest",
                        "tool": "documents",
                        "status": "empty",
                        "latency_ms": None,
                        "trace_id": TRACE_ID.get(),
                    }
                )
            except Exception as e:
                logger.debug("audit_event_failed", status="empty", error=str(e))
            return {"doc_id": doc_id, "chunks": 0, "status": "empty"}

        # Embed chunks
        import time

        _t0 = time.perf_counter()
        vectors = await aembed_texts(chunks)
        self._metrics.record_ingest_latency(time.perf_counter() - _t0)

        collection_name = await aget_or_create_collection(f"user_{user_id}")
        client = get_async_qdrant_client()

        # Check quota
        try:
            from qdrant_client import models as _models
            from app.config import settings

            max_points_user = int(
                getattr(settings, "DOC_INDEX_MAX_POINTS_PER_USER", 500000) or 500000
            )
            qfilter_user = _models.Filter(
                must=[
                    _models.FieldCondition(
                        key="metadata.type", match=_models.MatchValue(value="doc_chunk")
                    ),
                    _models.FieldCondition(
                        key="metadata.user_id", match=_models.MatchValue(value=str(user_id))
                    ),
                ]
            )
            cnt_user = await client.count(
                collection_name=collection_name, count_filter=qfilter_user, exact=True
            )
            cur_user = int(getattr(cnt_user, "count", 0) or 0)

            if cur_user >= max_points_user:
                self._metrics.record_ingest_status("quota_exceeded", user_id)
                logger.warning(
                    "document_quota_exceeded",
                    user_id=user_id,
                    current=cur_user,
                    limit=max_points_user,
                )
                return {"doc_id": doc_id, "chunks": 0, "status": "quota_exceeded"}
        except Exception as e:
            logger.warning("quota_check_failed", user_id=user_id, error=str(e))

        # Build points
        points: list[models.PointStruct] = []
        ts_ms = int(time.time() * 1000)

        for i, vec in enumerate(vectors):
            pid = str(uuid4())

            # Hash de conteúdo normalizado para dedupe
            norm = re.sub(r"\s+", " ", chunks[i]).strip().lower()
            content_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()

            # Verificar duplicidade existente
            dup_status = "unique"
            try:
                from qdrant_client import models as _models

                qfilter_hash = _models.Filter(
                    must=[
                        _models.FieldCondition(
                            key="metadata.content_hash",
                            match=_models.MatchValue(value=content_hash),
                        ),
                        _models.FieldCondition(
                            key="metadata.user_id", match=_models.MatchValue(value=str(user_id))
                        ),
                    ]
                )
                cnt_hash = await client.count(
                    collection_name=collection_name, count_filter=qfilter_hash, exact=True
                )
                if int(getattr(cnt_hash, "count", 0) or 0) > 0:
                    dup_status = "duplicate"
            except Exception as e:
                logger.debug("duplicate_check_failed", chunk_index=i, error=str(e))

            payload = {
                "metadata": {
                    "type": "doc_chunk",
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "file_name": filename,
                    "timestamp": ts_ms,
                    "index": i,
                    "content_hash": content_hash,
                    "status": dup_status,
                    "conversation_id": conversation_id,
                },
                "content": chunks[i][:2000],
            }
            points.append(models.PointStruct(id=pid, vector=vec, payload=payload))

        # Upsert points
        await client.upsert(collection_name=collection_name, points=points)

        # Record success metrics
        self._metrics.record_ingest_success("indexed", len(points), user_id)

        # Record audit event
        try:
            record_audit_event_direct(
                {
                    "user_id": int(user_id) if user_id is not None else None,
                    "endpoint": "doc:ingest",
                    "action": "ingest",
                    "tool": "documents",
                    "status": "indexed",
                    "latency_ms": int((time.perf_counter() - _t0) * 1000),
                    "trace_id": TRACE_ID.get(),
                }
            )
        except Exception as e:
            logger.debug("audit_event_failed", status="indexed", error=str(e))

        return {"doc_id": doc_id, "chunks": len(chunks), "status": "indexed"}
