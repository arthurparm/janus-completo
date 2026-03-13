from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
from fastapi import UploadFile
from qdrant_client import models

from app.config import settings
from app.core.embeddings.embedding_manager import aembed_texts
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.core.workers.document_ingestion_worker import publish_document_ingestion_task
from app.db.vector_store import (
    aget_or_create_collection,
    async_count_points,
    build_deterministic_point_id,
    build_user_docs_collection_name,
    get_async_qdrant_client,
)
from app.repositories.document_manifest_repository import DocumentManifestRepository
from app.repositories.observability_repository import record_audit_event_direct
from app.services.document_parser_service import DocumentParserService
from app.services.document_semantic_enrichment_service import DocumentSemanticEnrichmentService
from app.services.outbox_service import OutboxService

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None

from app.core.monitoring.document_metrics import get_metrics_recorder

logger = structlog.get_logger(__name__)


class DocumentFileTooLargeError(Exception):
    def __init__(self, size_bytes: int, max_bytes: int, doc_id: str):
        super().__init__(f"Arquivo excede o limite de {max_bytes} bytes")
        self.size_bytes = int(size_bytes)
        self.max_bytes = int(max_bytes)
        self.doc_id = str(doc_id)


class DocumentIngestionService:
    def __init__(
        self,
        memory_service: Any | None = None,
        manifest_repo: DocumentManifestRepository | None = None,
        outbox_service: OutboxService | None = None,
    ):
        self._memory_service = memory_service
        self._parser = DocumentParserService()
        self._semantic_enricher = DocumentSemanticEnrichmentService()
        self._metrics = get_metrics_recorder()
        self._manifest_repo = manifest_repo or DocumentManifestRepository()
        self._outbox_service = outbox_service

    def build_doc_id(self, user_id: str) -> str:
        return f"doc:{user_id}:{uuid4().hex}"

    def storage_root(self) -> Path:
        value = getattr(settings, "DOC_UPLOAD_STORAGE_DIR", "/app/data/document_uploads")
        return Path(str(value)).expanduser()

    def resolve_storage_path(self, *, user_id: str, doc_id: str, filename: str) -> Path:
        safe_name = Path(filename or "document").name or "document"
        return self.storage_root() / str(user_id) / str(doc_id) / safe_name

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
        if not text:
            return []
        chunks: list[str] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunks.append(text[start:end])
            if end >= n:
                break
            start = max(0, end - overlap)
        return chunks

    async def stage_upload(
        self,
        *,
        file: UploadFile,
        user_id: str,
        conversation_id: str | None,
        knowledge_space_id: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        doc_role: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
        auto_consolidate: bool = False,
    ) -> dict[str, Any]:
        doc_id = self.build_doc_id(user_id)
        filename = Path(file.filename or "document").name or "document"
        content_type = (file.content_type or "application/octet-stream").strip()
        storage_path = self.resolve_storage_path(user_id=user_id, doc_id=doc_id, filename=filename)
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = self._manifest_repo.create_manifest(
            doc_id=doc_id,
            user_id=str(user_id),
            conversation_id=str(conversation_id) if conversation_id is not None else None,
            knowledge_space_id=str(knowledge_space_id) if knowledge_space_id is not None else None,
            source_type=str(source_type) if source_type is not None else None,
            source_id=str(source_id) if source_id is not None else None,
            doc_role=str(doc_role) if doc_role is not None else None,
            edition_or_version=(
                str(edition_or_version) if edition_or_version is not None else None
            ),
            language=str(language) if language is not None else None,
            parent_collection_id=(
                str(parent_collection_id) if parent_collection_id is not None else None
            ),
            file_name=filename,
            content_type=content_type,
            file_size_bytes=0,
            status="queued",
            storage_path=str(storage_path),
        )
        max_bytes = int(getattr(settings, "DOCS_MAX_FILE_SIZE_BYTES", 100_000_000) or 100_000_000)
        chunk_bytes = int(getattr(settings, "DOC_UPLOAD_STREAM_CHUNK_BYTES", 1_048_576) or 1_048_576)
        written = 0

        try:
            with storage_path.open("wb") as handle:
                while True:
                    chunk = await file.read(chunk_bytes)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise DocumentFileTooLargeError(written, max_bytes, doc_id)
                    handle.write(chunk)
        except DocumentFileTooLargeError:
            self._manifest_repo.mark_failed(
                doc_id,
                status="file_too_large",
                error_code="file_too_large",
                error_message=f"Arquivo excede o limite de {max_bytes} bytes",
                file_size_bytes=written,
            )
            self.cleanup_staged_file(storage_path)
            raise
        except Exception as exc:
            self._manifest_repo.mark_failed(
                doc_id,
                status="failed",
                error_code="upload_failed",
                error_message=str(exc),
                file_size_bytes=written,
            )
            self.cleanup_staged_file(storage_path)
            raise
        finally:
            try:
                await file.close()
            except Exception:
                pass

        self._manifest_repo.update_manifest(doc_id, file_size_bytes=written)
        payload = {
            "doc_id": doc_id,
            "auto_consolidate": bool(auto_consolidate),
        }
        dedupe_key = f"document_ingestion:{doc_id}"
        if self._outbox_service is not None:
            self._outbox_service.enqueue_document_ingestion(
                payload=payload,
                aggregate_id=doc_id,
                dedupe_key=dedupe_key,
            )
        else:
            await publish_document_ingestion_task(payload)

        return {
            "doc_id": doc_id,
            "status": "queued",
            "message": "Documento recebido e enfileirado para indexação.",
            "status_endpoint": f"/api/v1/documents/status/{doc_id}",
            "chunks": 0,
            "file_size_bytes": written,
        }

    def cleanup_staged_file(self, storage_path: str | Path | None) -> None:
        if not storage_path:
            return
        try:
            path = Path(str(storage_path))
            if path.exists():
                path.unlink()
            parent = path.parent
            while parent != parent.parent and parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        except Exception as exc:
            logger.debug("document_storage_cleanup_failed", path=str(storage_path), error=str(exc))

    async def process_staged_document(self, *, doc_id: str) -> dict[str, Any]:
        manifest = self._manifest_repo.get_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Manifesto não encontrado para {doc_id}")

        storage_path = manifest.get("storage_path")
        if not storage_path or not Path(str(storage_path)).exists():
            self._manifest_repo.mark_failed(
                doc_id,
                status="failed",
                error_code="missing_storage_file",
                error_message="Arquivo staged não encontrado",
            )
            raise FileNotFoundError(f"Arquivo staged não encontrado para {doc_id}")

        self._manifest_repo.mark_processing(doc_id)

        try:
            data = Path(str(storage_path)).read_bytes()
            result = await self._ingest_payload(
                doc_id=doc_id,
                user_id=str(manifest["user_id"]),
                filename=str(manifest["file_name"]),
                content_type=str(manifest.get("content_type") or ""),
                data=data,
                conversation_id=str(manifest["conversation_id"]) if manifest.get("conversation_id") else None,
                knowledge_space_id=(
                    str(manifest["knowledge_space_id"]) if manifest.get("knowledge_space_id") else None
                ),
                source_type=str(manifest["source_type"]) if manifest.get("source_type") else None,
                source_id=str(manifest["source_id"]) if manifest.get("source_id") else None,
                doc_role=str(manifest["doc_role"]) if manifest.get("doc_role") else None,
                edition_or_version=(
                    str(manifest["edition_or_version"]) if manifest.get("edition_or_version") else None
                ),
                language=str(manifest["language"]) if manifest.get("language") else None,
                parent_collection_id=(
                    str(manifest["parent_collection_id"])
                    if manifest.get("parent_collection_id")
                    else None
                ),
                file_size_bytes=int(manifest.get("file_size_bytes") or len(data)),
                progress_cb=self._progress_callback(doc_id),
            )

            status = str(result.get("status") or "")
            if status == "indexed":
                semantic = result.get("semantic") or {}
                self._manifest_repo.mark_completed(
                    doc_id,
                    chunks_total=int(result.get("chunks", 0)),
                    chunks_indexed=int(result.get("chunks_indexed", result.get("chunks", 0))),
                    semantic_doc_type=semantic.get("doc_type"),
                    semantic_summary=semantic.get("summary"),
                    semantic_confidence=semantic.get("confidence"),
                )
            else:
                self._manifest_repo.mark_failed(
                    doc_id,
                    status=status or "failed",
                    error_code=status or "failed",
                    error_message=str(result.get("error") or status or "Falha ao processar documento"),
                    chunks_total=int(result.get("chunks", 0)),
                    chunks_indexed=int(result.get("chunks_indexed", 0)),
                    file_size_bytes=int(manifest.get("file_size_bytes") or len(data)),
                )
            return result
        except Exception as exc:
            await self._delete_doc_points(user_id=str(manifest["user_id"]), doc_id=doc_id)
            self._manifest_repo.mark_failed(
                doc_id,
                status="failed",
                error_code=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        finally:
            self.cleanup_staged_file(storage_path)

    def _progress_callback(self, doc_id: str) -> Callable[..., Awaitable[None]]:
        async def _callback(**kwargs: Any) -> None:
            self._manifest_repo.update_progress(doc_id, **kwargs)

        return _callback

    async def ingest_file(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        conversation_id: str | None = None,
        knowledge_space_id: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        doc_role: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._ingest_payload(
            doc_id=self.build_doc_id(user_id),
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            data=data,
            conversation_id=conversation_id,
            knowledge_space_id=knowledge_space_id,
            source_type=source_type,
            source_id=source_id,
            doc_role=doc_role,
            edition_or_version=edition_or_version,
            language=language,
            parent_collection_id=parent_collection_id,
            file_size_bytes=len(data or b""),
        )

    async def _ingest_payload(
        self,
        *,
        doc_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        conversation_id: str | None = None,
        knowledge_space_id: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        doc_role: str | None = None,
        edition_or_version: str | None = None,
        language: str | None = None,
        parent_collection_id: str | None = None,
        file_size_bytes: int = 0,
        progress_cb: Callable[..., Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
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
                except Exception as exc:
                    logger.debug("otel_span_attribute_failed", error=str(exc))

        text = self._parser.parse(data, content_type, filename)
        if not text:
            logger.warning(
                "document_text_extraction_empty",
                filename=filename,
                content_type=content_type,
            )
            return {"doc_id": doc_id, "chunks": 0, "chunks_indexed": 0, "status": "unsupported_content_type"}

        semantic = self._semantic_enricher.enrich(
            text=text,
            filename=filename,
            content_type=content_type,
        )
        chunk_size = int(getattr(settings, "DOC_CHUNK_SIZE", 1000) or 1000)
        overlap = int(getattr(settings, "DOC_CHUNK_OVERLAP", 100) or 100)
        embed_batch_size = int(getattr(settings, "DOC_INGEST_EMBED_BATCH_SIZE", 32) or 32)
        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        chunk_count = len(chunks)
        self._metrics.record_chunks_count(chunk_count)

        if _OTEL and span is not None:
            try:
                span.set_attribute("doc.chunk_count", chunk_count)
                span.set_attribute("doc.semantic_type", semantic.doc_type)
                span.set_attribute("doc.semantic_confidence", float(semantic.confidence))
            except Exception as exc:
                logger.debug("otel_chunk_count_failed", error=str(exc))

        if not chunks:
            self._metrics.record_ingest_status("empty", user_id)
            return {"doc_id": doc_id, "chunks": 0, "chunks_indexed": 0, "status": "empty"}

        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        client = get_async_qdrant_client()
        qfilter_user = models.Filter(
            must=[
                models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
                models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
            ]
        )
        max_points_user = int(getattr(settings, "DOC_INDEX_MAX_POINTS_PER_USER", 500000) or 500000)
        try:
            current_points = await async_count_points(client, collection_name, qfilter_user, exact=True)
            if current_points + chunk_count > max_points_user:
                self._metrics.record_ingest_status("quota_exceeded", user_id)
                return {
                    "doc_id": doc_id,
                    "chunks": chunk_count,
                    "chunks_indexed": 0,
                    "status": "quota_exceeded",
                    "error": f"Quota excedida para o usuário ({current_points} + {chunk_count} > {max_points_user})",
                }
        except Exception as exc:
            logger.warning("quota_check_failed", user_id=user_id, error=str(exc))

        await self._delete_doc_points(user_id=user_id, doc_id=doc_id)
        if progress_cb is not None:
            await progress_cb(
                chunks_total=chunk_count,
                chunks_indexed=0,
                file_size_bytes=file_size_bytes,
                semantic_doc_type=semantic.doc_type,
                semantic_summary=semantic.summary,
                semantic_confidence=semantic.confidence,
            )

        indexed = 0
        ingest_started_at = time.perf_counter()
        for offset in range(0, chunk_count, max(1, embed_batch_size)):
            batch_chunks = chunks[offset : offset + max(1, embed_batch_size)]
            vectors = await aembed_texts(batch_chunks)
            points: list[models.PointStruct] = []
            ts_ms = int(time.time() * 1000)
            for batch_index, vec in enumerate(vectors):
                chunk_index = offset + batch_index
                norm = re.sub(r"\s+", " ", batch_chunks[batch_index]).strip().lower()
                content_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()
                pid = build_deterministic_point_id("doc-chunk", user_id, doc_id, chunk_index, content_hash)
                payload = {
                    "type": "doc_chunk",
                    "ts_ms": ts_ms,
                    "composite_id": f"doc:{user_id}:{doc_id}:{chunk_index}:{content_hash}",
                    "metadata": {
                        "type": "doc_chunk",
                        "user_id": str(user_id),
                        "doc_id": doc_id,
                        "file_name": filename,
                        "knowledge_space_id": knowledge_space_id,
                        "source_type": source_type,
                        "source_id": source_id,
                        "doc_role": doc_role,
                        "edition_or_version": edition_or_version,
                        "language": language,
                        "parent_collection_id": parent_collection_id,
                        "timestamp": ts_ms,
                        "ts_ms": ts_ms,
                        "index": chunk_index,
                        "content_hash": content_hash,
                        "status": "unique",
                        "conversation_id": conversation_id,
                        "semantic_doc_type": semantic.doc_type,
                        "semantic_entities": semantic.entities,
                        "semantic_summary": semantic.summary,
                        "semantic_confidence": semantic.confidence,
                        "origin": "documents.ingest_file",
                    },
                    "content": batch_chunks[batch_index][:2000],
                }
                points.append(models.PointStruct(id=pid, vector=vec, payload=payload))
            await client.upsert(collection_name=collection_name, points=points)
            indexed += len(points)
            if progress_cb is not None:
                await progress_cb(
                    chunks_total=chunk_count,
                    chunks_indexed=indexed,
                    file_size_bytes=file_size_bytes,
                    semantic_doc_type=semantic.doc_type,
                    semantic_summary=semantic.summary,
                    semantic_confidence=semantic.confidence,
                )

        self._metrics.record_ingest_latency(time.perf_counter() - ingest_started_at)
        self._metrics.record_ingest_success("indexed", indexed, user_id)
        try:
            record_audit_event_direct(
                {
                    "user_id": int(user_id) if str(user_id).isdigit() else None,
                    "endpoint": "doc:ingest",
                    "action": "ingest",
                    "tool": "documents",
                    "status": "indexed",
                    "latency_ms": int((time.perf_counter() - ingest_started_at) * 1000),
                    "trace_id": TRACE_ID.get(),
                }
            )
        except Exception as exc:
            logger.debug("audit_event_failed", status="indexed", error=str(exc))

        return {
            "doc_id": doc_id,
            "chunks": chunk_count,
            "chunks_indexed": indexed,
            "status": "indexed",
            "semantic": semantic.to_dict(),
        }

    async def _delete_doc_points(self, *, user_id: str, doc_id: str) -> None:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(user_id))
        qfilter = models.Filter(
            must=[
                models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=str(user_id))),
                models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=str(doc_id))),
            ]
        )
        try:
            await client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=qfilter),
            )
        except Exception as exc:
            logger.debug("document_points_cleanup_failed", doc_id=doc_id, error=str(exc))
