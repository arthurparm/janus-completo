from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.document_service import DocumentFileTooLargeError, DocumentIngestionService

try:
    from prometheus_client import Counter, Histogram  # type: ignore

    _DOC_UPLOAD_REQ = Counter("doc_upload_requests_total", "Upload de documentos", ["status"])  # type: ignore
    _DOC_UPLOAD_LAT = Histogram("doc_upload_latency_seconds", "Latência de upload de documentos")  # type: ignore
    _DOC_SEARCH_REQ = Counter("doc_search_requests_total", "Busca de documentos", ["status"])  # type: ignore
    _DOC_SEARCH_LAT = Histogram("doc_search_latency_seconds", "Latência de busca de documentos")  # type: ignore
    _DOC_STATUS_REQ = Counter(
        "doc_status_requests_total", "Consulta de status de documento", ["status"]
    )  # type: ignore
    _DOC_STATUS_LAT = Histogram("doc_status_latency_seconds", "Latência de status de documento")  # type: ignore
except Exception:

    class _Noop:
        def labels(self, *a, **k):
            return self

        def inc(self, *a, **k):
            pass

        def observe(self, *a, **k):
            pass

    _DOC_UPLOAD_REQ = _Noop()
    _DOC_UPLOAD_LAT = _Noop()
    _DOC_SEARCH_REQ = _Noop()
    _DOC_SEARCH_LAT = _Noop()
    _DOC_STATUS_REQ = _Noop()
    _DOC_STATUS_LAT = _Noop()
try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None

router = APIRouter(tags=["Documents"])


def get_doc_service(request: Request) -> DocumentIngestionService:
    return request.app.state.document_service


def get_knowledge_facade(request: Request):
    return request.app.state.knowledge_facade


def _resolve_upload_user_scope(
    request: Request | None,
) -> str | None:
    return "default"


class UploadResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str
    message: str | None = None
    status_endpoint: str | None = None
    consolidation: dict[str, Any] | None = None
    semantic: dict[str, Any] | None = None
    knowledge_space_id: str | None = None
    doc_role: str | None = None


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    request: Request = None,
    service: DocumentIngestionService = Depends(get_doc_service),
    auto_consolidate: bool | None = Form(False),
    conversation_id: str | None = Form(None),
    knowledge_space_id: str | None = Form(None),
    source_type: str | None = Form(None),
    source_id: str | None = Form(None),
    doc_role: str | None = Form(None),
    edition_or_version: str | None = Form(None),
    language: str | None = Form(None),
    parent_collection_id: str | None = Form(None)):
    import time as _t

    _t0 = _t.perf_counter()
    try:
        cm = _tracer.start_as_current_span("docs.upload") if _OTEL else nullcontext()
        with cm:  # type: ignore
            result = await service.stage_upload(
                file=file,
                user_id="default",
                conversation_id=conversation_id,
                knowledge_space_id=knowledge_space_id,
                source_type=source_type,
                source_id=source_id,
                doc_role=doc_role,
                edition_or_version=edition_or_version,
                language=language,
                parent_collection_id=parent_collection_id,
                auto_consolidate=bool(auto_consolidate))
    except DocumentFileTooLargeError as exc:
        payload = UploadResponse(
            doc_id=exc.doc_id,
            chunks=0,
            status="file_too_large",
            message=str(exc),
            status_endpoint=f"/api/v1/documents/status/{exc.doc_id}")
        _DOC_UPLOAD_REQ.labels("file_too_large").inc()
        _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=payload.model_dump())
    except Exception as exc:
        _DOC_UPLOAD_REQ.labels("error").inc()
        _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao enfileirar documento: {exc}") from exc

    _DOC_UPLOAD_REQ.labels(str(result.get("status") or "queued")).inc()
    _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    return UploadResponse(
        doc_id=result.get("doc_id"),
        chunks=result.get("chunks"),
        status=result.get("status"),
        message=result.get("message"),
        status_endpoint=result.get("status_endpoint"),
        semantic=result.get("semantic"),
        knowledge_space_id=knowledge_space_id,
        doc_role=doc_role)


class DocSearchResponse(BaseModel):
    results: list[dict[str, Any]]


@router.get("/search", response_model=DocSearchResponse)
async def search_documents(
    query: str = Query(...),
    doc_id: str | None = None,
    knowledge_space_id: str | None = None,
    limit: int = 5,
    min_score: float | None = None,
    request: Request = None,
    knowledge = Depends(get_knowledge_facade)):
    import time as _t

    _t0 = _t.perf_counter()
    uid = "default"
    if not uid:
        _DOC_SEARCH_REQ.labels("error").inc()
        _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return DocSearchResponse(results=[])
    cm = _tracer.start_as_current_span("docs.search") if _OTEL else nullcontext()
    with cm:  # type: ignore
        results = await knowledge.search_documents(
            query=query,
            user_id=uid,
            doc_id=doc_id,
            knowledge_space_id=knowledge_space_id,
            limit=limit,
            min_score=min_score,
        )
    _DOC_SEARCH_REQ.labels("success").inc()
    _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    return DocSearchResponse(results=results)


class DocListItem(BaseModel):
    doc_id: str
    knowledge_space_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    doc_role: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    file_name: str | None
    chunks: int
    chunks_total: int = 0
    chunks_indexed: int = 0
    status: str | None = None
    conversation_id: str | None
    last_index_ts: int | None
    semantic_doc_type: str | None = None
    semantic_confidence: float | None = None
    semantic_summary: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class DocListResponse(BaseModel):
    items: list[DocListItem]


@router.get("/list", response_model=DocListResponse)
async def list_documents(
    conversation_id: str | None = None,
    knowledge_space_id: str | None = None,
    request: Request = None,
    limit: int = 100,
    knowledge = Depends(get_knowledge_facade)):
    uid = "default"
    if not uid:
        return DocListResponse(items=[])

    service: DocumentIngestionService = request.app.state.document_service
    manifest_rows = service._manifest_repo.list_manifests(
        user_id="default",
        conversation_id=conversation_id,
        knowledge_space_id=knowledge_space_id,
        limit=limit)
    items: list[DocListItem] = []
    for row in manifest_rows:
        doc_id = str(row.get("doc_id"))
        chunks_total = int(row.get("chunks_total") or 0)
        chunks_indexed = int(row.get("chunks_indexed") or 0)
        items.append(
            DocListItem(
                doc_id=doc_id,
                knowledge_space_id=row.get("knowledge_space_id"),
                source_type=row.get("source_type"),
                source_id=row.get("source_id"),
                doc_role=row.get("doc_role"),
                edition_or_version=row.get("edition_or_version"),
                language=row.get("language"),
                parent_collection_id=row.get("parent_collection_id"),
                file_name=row.get("file_name"),
                chunks=chunks_total,
                chunks_total=chunks_total,
                chunks_indexed=chunks_indexed,
                status=row.get("status"),
                conversation_id=row.get("conversation_id"),
                last_index_ts=None,
                semantic_doc_type=row.get("semantic_doc_type"),
                semantic_confidence=row.get("semantic_confidence"),
                semantic_summary=row.get("semantic_summary"),
                created_at=row.get("created_at"),
                started_at=row.get("started_at"),
                completed_at=row.get("completed_at"))
        )
    return DocListResponse(items=items)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, request: Request = None, knowledge = Depends(get_knowledge_facade)):
    uid = "default"
    try:
        await knowledge.delete_document(doc_id=doc_id, user_id=uid)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao excluir documento: {exc}") from exc

    service = request.app.state.document_service
    manifest = service._manifest_repo.get_manifest(doc_id, uid)
    if manifest is not None:
        service.cleanup_staged_file(manifest.get("storage_path"))
        service._manifest_repo.delete_manifest(doc_id, uid)
    return {"status": "ok"}


ALLOWED_LINK_URL_HOSTS = {
    "example.com",
    "www.example.com",
}


def _is_allowed_link_url(raw_url: str) -> bool:
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower().strip(".")
    return hostname in ALLOWED_LINK_URL_HOSTS


def _is_public_http_url(raw_url: str) -> bool:
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    lowered = hostname.lower().strip(".")
    if lowered in {"localhost"} or lowered.endswith(".localhost"):
        return False

    try:
        addrinfo = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except Exception:
        return False

    for entry in addrinfo:
        ip_text = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_text)
        except ValueError:
            return False

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return False

    return True


class LinkUrlResponse(BaseModel):
    doc_id: str
    status: str
    chunks: int
    semantic: dict[str, Any] | None = None
    knowledge_space_id: str | None = None
    doc_role: str | None = None


@router.post("/link-url", response_model=LinkUrlResponse)
async def link_url(
    url: str = Form(...),
    conversation_id: str | None = Form(None),
    knowledge_space_id: str | None = Form(None),
    source_type: str | None = Form(None),
    source_id: str | None = Form(None),
    doc_role: str | None = Form(None),
    edition_or_version: str | None = Form(None),
    language: str | None = Form(None),
    parent_collection_id: str | None = Form(None),
    request: Request = None,
    service: DocumentIngestionService = Depends(get_doc_service)):
    import httpx

    if not _is_allowed_link_url(url) or not _is_public_http_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL inválida ou não permitida",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, follow_redirects=False)
            content_type = resp.headers.get("content-type", "text/html")
            data = resp.content
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falha ao obter URL") from exc

    filename = url.split("/")[-1] or "page.html"
    result = await service.ingest_file(
        user_id="default",
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
        parent_collection_id=parent_collection_id)
    if result.get("status") == "indexed":
        service._manifest_repo.create_manifest(
            doc_id=result.get("doc_id"),
            user_id="default",
            conversation_id=conversation_id,
            knowledge_space_id=knowledge_space_id,
            source_type=source_type,
            source_id=source_id,
            doc_role=doc_role,
            edition_or_version=edition_or_version,
            language=language,
            parent_collection_id=parent_collection_id,
            file_name=filename,
            content_type=content_type,
            file_size_bytes=len(data or b""),
            status="indexed",
            storage_path=None)
        service._manifest_repo.mark_completed(
            result.get("doc_id"),
            chunks_total=int(result.get("chunks") or 0),
            chunks_indexed=int(result.get("chunks_indexed", result.get("chunks") or 0)),
            semantic_doc_type=(result.get("semantic") or {}).get("doc_type"),
            semantic_summary=(result.get("semantic") or {}).get("summary"),
            semantic_confidence=(result.get("semantic") or {}).get("confidence"))
    return LinkUrlResponse(
        doc_id=result.get("doc_id"),
        status=result.get("status"),
        chunks=result.get("chunks"),
        semantic=result.get("semantic"),
        knowledge_space_id=knowledge_space_id,
        doc_role=doc_role)


class DocStatusResponse(BaseModel):
    doc_id: str
    knowledge_space_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    status: str
    chunks_total: int = 0
    chunks_indexed: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    samples: list[dict[str, Any]]
    semantic: dict[str, Any] | None = None


def _build_doc_samples(points: list[Any]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for hit in points or []:
        payload = getattr(hit, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        samples.append(
            {
                "id": getattr(hit, "id", None),
                "file_name": meta.get("file_name"),
                "index": meta.get("index"),
                "content": payload.get("content"),
                "semantic_doc_type": meta.get("semantic_doc_type"),
                "semantic_confidence": meta.get("semantic_confidence"),
                "knowledge_space_id": meta.get("knowledge_space_id"),
                "section_title": meta.get("section_title"),
            }
        )
    return samples


@router.get("/status/{doc_id}", response_model=DocStatusResponse)
async def document_status(doc_id: str, request: Request = None, knowledge = Depends(get_knowledge_facade)):
    import time as _t

    _t0 = _t.perf_counter()
    uid = "default"

    service = request.app.state.document_service
    manifest = service._manifest_repo.get_manifest(doc_id, uid)
    if manifest is not None:
        semantic_payload = None
        if manifest.get("semantic_doc_type") or manifest.get("semantic_summary"):
            semantic_payload = {
                "doc_type": manifest.get("semantic_doc_type"),
                "confidence_avg": manifest.get("semantic_confidence"),
                "summary": manifest.get("semantic_summary"),
                "type_counts": (
                    {str(manifest.get("semantic_doc_type")): int(manifest.get("chunks_indexed") or 0)}
                    if manifest.get("semantic_doc_type")
                    else {}
                ),
            }

        samples: list[dict[str, Any]] = []
        if manifest.get("status") == "indexed":
            cm = _tracer.start_as_current_span("docs.status") if _OTEL else nullcontext()
            with cm:  # type: ignore
                points, _ = await knowledge.get_document_points(doc_id=doc_id, user_id=uid, limit=10)
            samples = _build_doc_samples(points)

        _DOC_STATUS_REQ.labels("success").inc()
        _DOC_STATUS_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return DocStatusResponse(
            doc_id=doc_id,
            knowledge_space_id=manifest.get("knowledge_space_id"),
            source_type=manifest.get("source_type"),
            source_id=manifest.get("source_id"),
            edition_or_version=manifest.get("edition_or_version"),
            language=manifest.get("language"),
            parent_collection_id=manifest.get("parent_collection_id"),
            status=str(manifest.get("status") or "queued"),
            chunks_total=int(manifest.get("chunks_total") or 0),
            chunks_indexed=int(manifest.get("chunks_indexed") or 0),
            error_code=manifest.get("error_code"),
            error_message=manifest.get("error_message"),
            created_at=manifest.get("created_at"),
            started_at=manifest.get("started_at"),
            completed_at=manifest.get("completed_at"),
            samples=samples,
            semantic=semantic_payload)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document manifest not found")
