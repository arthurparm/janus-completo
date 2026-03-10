from __future__ import annotations

from typing import Any

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
from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.security.request_guard import get_request_actor_id, resolve_user_scope_id
from app.db.vector_store import (
    aget_or_create_collection,
    async_count_points,
    build_user_docs_collection_name,
    get_async_qdrant_client,
)
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


def _resolve_upload_user_scope(
    request: Request | None,
    *,
    user_id_query: str | None,
    user_id_form: str | None,
) -> str | None:
    candidates: dict[str, str] = {}
    if user_id_query:
        candidates["query"] = str(user_id_query)
    if user_id_form:
        candidates["form"] = str(user_id_form)
    actor_id = get_request_actor_id(request)
    if actor_id is not None:
        candidates["actor"] = str(actor_id)
    if not candidates:
        return None
    values = {value for value in candidates.values() if value}
    if len(values) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="user_id conflitante entre query/form/auth",
        )
    return values.pop() if values else None


class UploadResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str
    message: str | None = None
    status_endpoint: str | None = None
    consolidation: dict[str, Any] | None = None
    semantic: dict[str, Any] | None = None


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str | None = Query(None),
    user_id_form: str | None = Form(None),
    request: Request = None,
    service: DocumentIngestionService = Depends(get_doc_service),
    auto_consolidate: bool | None = Form(False),
    conversation_id: str | None = Form(None),
):
    import time as _t

    _t0 = _t.perf_counter()
    uid = _resolve_upload_user_scope(request, user_id_query=user_id, user_id_form=user_id_form)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="user_id necessário"
        )
    try:
        cm = _tracer.start_as_current_span("docs.upload") if _OTEL else nullcontext()
        with cm:  # type: ignore
            result = await service.stage_upload(
                file=file,
                user_id=uid,
                conversation_id=conversation_id,
                auto_consolidate=bool(auto_consolidate),
            )
    except DocumentFileTooLargeError as exc:
        payload = UploadResponse(
            doc_id=exc.doc_id,
            chunks=0,
            status="file_too_large",
            message=str(exc),
            status_endpoint=f"/api/v1/documents/status/{exc.doc_id}",
        )
        _DOC_UPLOAD_REQ.labels("file_too_large").inc()
        _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=payload.model_dump(),
        )
    except Exception as exc:
        _DOC_UPLOAD_REQ.labels("error").inc()
        _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao enfileirar documento: {exc}",
        ) from exc

    _DOC_UPLOAD_REQ.labels(str(result.get("status") or "queued")).inc()
    _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    return UploadResponse(
        doc_id=result.get("doc_id"),
        chunks=result.get("chunks"),
        status=result.get("status"),
        message=result.get("message"),
        status_endpoint=result.get("status_endpoint"),
        semantic=result.get("semantic"),
    )


class DocSearchResponse(BaseModel):
    results: list[dict[str, Any]]


@router.get("/search", response_model=DocSearchResponse)
async def search_documents(
    query: str = Query(...),
    user_id: str | None = None,
    doc_id: str | None = None,
    limit: int = 5,
    min_score: float | None = None,
    request: Request = None,
):
    import time as _t

    _t0 = _t.perf_counter()
    uid = resolve_user_scope_id(request, user_id)
    if not uid:
        _DOC_SEARCH_REQ.labels("error").inc()
        _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return DocSearchResponse(results=[])
    vec = await aembed_text(query)
    client = get_async_qdrant_client()
    collection_name = await aget_or_create_collection(build_user_docs_collection_name(uid))
    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=uid)),
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
    ]
    if doc_id:
        must.append(
            models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))
        )
    sc_filter = models.Filter(must=must)
    cm = _tracer.start_as_current_span("docs.search") if _OTEL else nullcontext()
    with cm:  # type: ignore
        res = await client.query_points(
            collection_name=collection_name,
            query=vec,
            limit=limit,
            with_payload=True,
            query_filter=sc_filter,
            score_threshold=min_score if isinstance(min_score, float) else None,
        )
    points = getattr(res, "points", res) or []
    results: list[dict[str, Any]] = []
    for point in points:
        payload = point.payload or {}
        meta = payload.get("metadata", {})
        results.append(
            {
                "id": point.id,
                "score": point.score,
                "doc_id": meta.get("doc_id"),
                "file_name": meta.get("file_name"),
                "index": meta.get("index"),
                "timestamp": meta.get("timestamp"),
            }
        )
    _DOC_SEARCH_REQ.labels("success").inc()
    _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    return DocSearchResponse(results=results)


class DocListItem(BaseModel):
    doc_id: str
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


def _build_legacy_doc_list_item(doc_id: str, payload: dict[str, Any]) -> DocListItem:
    return DocListItem(
        doc_id=doc_id,
        file_name=payload.get("file_name"),
        chunks=int(payload.get("chunks", 0)),
        chunks_total=int(payload.get("chunks", 0)),
        chunks_indexed=int(payload.get("chunks", 0)),
        status="indexed",
        conversation_id=payload.get("conversation_id"),
        last_index_ts=payload.get("last_index_ts"),
        semantic_doc_type=payload.get("semantic_doc_type"),
        semantic_confidence=payload.get("semantic_confidence"),
        semantic_summary=payload.get("semantic_summary"),
    )


@router.get("/list", response_model=DocListResponse)
async def list_documents(
    user_id: str | None = None,
    conversation_id: str | None = None,
    request: Request = None,
    limit: int = 100,
):
    uid = resolve_user_scope_id(request, user_id)
    if not uid:
        return DocListResponse(items=[])

    service: DocumentIngestionService = request.app.state.document_service
    manifest_rows = service._manifest_repo.list_manifests(
        user_id=uid,
        conversation_id=conversation_id,
        limit=limit,
    )
    items: list[DocListItem] = []
    seen_doc_ids: set[str] = set()
    for row in manifest_rows:
        doc_id = str(row.get("doc_id"))
        seen_doc_ids.add(doc_id)
        chunks_total = int(row.get("chunks_total") or 0)
        chunks_indexed = int(row.get("chunks_indexed") or 0)
        items.append(
            DocListItem(
                doc_id=doc_id,
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
                completed_at=row.get("completed_at"),
            )
        )

    client = get_async_qdrant_client()
    coll = await aget_or_create_collection(build_user_docs_collection_name(uid))
    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=uid)),
    ]
    if conversation_id:
        must.append(
            models.FieldCondition(
                key="metadata.conversation_id", match=models.MatchValue(value=conversation_id)
            )
        )
    qfilter = models.Filter(must=must)
    scroll_res = await client.scroll(
        collection_name=coll,
        scroll_filter=qfilter,
        limit=limit,
        with_payload=True,
    )
    points = scroll_res[0] if isinstance(scroll_res, tuple) else (scroll_res or [])
    agg: dict[str, dict[str, Any]] = {}
    for hit in points:
        payload = getattr(hit, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        did = str(meta.get("doc_id") or "")
        if not did or did in seen_doc_ids:
            continue
        current = agg.get(did) or {
            "doc_id": did,
            "file_name": meta.get("file_name"),
            "chunks": 0,
            "conversation_id": meta.get("conversation_id"),
            "last_index_ts": 0,
            "semantic_doc_type": meta.get("semantic_doc_type"),
            "semantic_confidence": meta.get("semantic_confidence"),
            "semantic_summary": meta.get("semantic_summary"),
        }
        current["chunks"] = int(current.get("chunks", 0)) + 1
        ts = int(meta.get("timestamp") or 0)
        if ts > int(current.get("last_index_ts") or 0):
            current["last_index_ts"] = ts
        agg[did] = current
    for doc_id, payload in agg.items():
        items.append(_build_legacy_doc_list_item(doc_id, payload))
    return DocListResponse(items=items)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, user_id: str | None = None, request: Request = None):
    uid = resolve_user_scope_id(request, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="user_id necessário"
        )
    client = get_async_qdrant_client()
    coll = await aget_or_create_collection(build_user_docs_collection_name(uid))
    try:
        qfilter = models.Filter(
            must=[
                models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=uid)),
                models.FieldCondition(
                    key="metadata.type", match=models.MatchValue(value="doc_chunk")
                ),
                models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id)),
            ]
        )
        await client.delete(
            collection_name=coll,
            points_selector=models.FilterSelector(filter=qfilter),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao excluir documento: {exc}",
        ) from exc

    service = request.app.state.document_service
    manifest = service._manifest_repo.get_manifest(doc_id, uid)
    if manifest is not None:
        service.cleanup_staged_file(manifest.get("storage_path"))
        service._manifest_repo.delete_manifest(doc_id, uid)
    return {"status": "ok"}


class LinkUrlResponse(BaseModel):
    doc_id: str
    status: str
    chunks: int
    semantic: dict[str, Any] | None = None


@router.post("/link-url", response_model=LinkUrlResponse)
async def link_url(
    url: str = Form(...),
    user_id: str | None = None,
    conversation_id: str | None = Form(None),
    request: Request = None,
    service: DocumentIngestionService = Depends(get_doc_service),
):
    uid = resolve_user_scope_id(request, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="user_id necessário"
        )
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "text/html")
            data = resp.content
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falha ao obter URL") from exc

    filename = url.split("/")[-1] or "page.html"
    result = await service.ingest_file(
        user_id=uid,
        filename=filename,
        content_type=content_type,
        data=data,
        conversation_id=conversation_id,
    )
    if result.get("status") == "indexed":
        service._manifest_repo.create_manifest(
            doc_id=result.get("doc_id"),
            user_id=uid,
            conversation_id=conversation_id,
            file_name=filename,
            content_type=content_type,
            file_size_bytes=len(data or b""),
            status="indexed",
            storage_path=None,
        )
        service._manifest_repo.mark_completed(
            result.get("doc_id"),
            chunks_total=int(result.get("chunks") or 0),
            chunks_indexed=int(result.get("chunks_indexed", result.get("chunks") or 0)),
            semantic_doc_type=(result.get("semantic") or {}).get("doc_type"),
            semantic_summary=(result.get("semantic") or {}).get("summary"),
            semantic_confidence=(result.get("semantic") or {}).get("confidence"),
        )
    return LinkUrlResponse(
        doc_id=result.get("doc_id"),
        status=result.get("status"),
        chunks=result.get("chunks"),
        semantic=result.get("semantic"),
    )


class DocStatusResponse(BaseModel):
    doc_id: str
    user_id: str
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
            }
        )
    return samples


@router.get("/status/{doc_id}", response_model=DocStatusResponse)
async def document_status(doc_id: str, user_id: str | None = None, request: Request = None):
    import time as _t

    _t0 = _t.perf_counter()
    uid = resolve_user_scope_id(request, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="user_id necessário"
        )

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
            client = get_async_qdrant_client()
            coll = await aget_or_create_collection(build_user_docs_collection_name(uid))
            qfilter = models.Filter(
                must=[models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))]
            )
            cm = _tracer.start_as_current_span("docs.status") if _OTEL else nullcontext()
            with cm:  # type: ignore
                res = await client.query_points(
                    collection_name=coll,
                    query=[0.0] * 1536,
                    limit=10,
                    with_payload=True,
                    query_filter=qfilter,
                )
            samples = _build_doc_samples(getattr(res, "points", res) or [])

        _DOC_STATUS_REQ.labels("success").inc()
        _DOC_STATUS_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return DocStatusResponse(
            doc_id=doc_id,
            user_id=uid,
            status=str(manifest.get("status") or "queued"),
            chunks_total=int(manifest.get("chunks_total") or 0),
            chunks_indexed=int(manifest.get("chunks_indexed") or 0),
            error_code=manifest.get("error_code"),
            error_message=manifest.get("error_message"),
            created_at=manifest.get("created_at"),
            started_at=manifest.get("started_at"),
            completed_at=manifest.get("completed_at"),
            samples=samples,
            semantic=semantic_payload,
        )

    client = get_async_qdrant_client()
    coll = await aget_or_create_collection(build_user_docs_collection_name(uid))
    qfilter = models.Filter(
        must=[models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))]
    )
    cm = _tracer.start_as_current_span("docs.status") if _OTEL else nullcontext()
    with cm:  # type: ignore
        res = await client.query_points(
            collection_name=coll,
            query=[0.0] * 1536,
            limit=10,
            with_payload=True,
            query_filter=qfilter,
        )
    points = getattr(res, "points", res) or []
    samples = _build_doc_samples(points)
    total = await async_count_points(client, coll, qfilter, exact=True)
    _DOC_STATUS_REQ.labels("success").inc()
    _DOC_STATUS_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    return DocStatusResponse(
        doc_id=doc_id,
        user_id=uid,
        status="indexed",
        chunks_total=total,
        chunks_indexed=total,
        samples=samples,
        semantic=None,
    )
