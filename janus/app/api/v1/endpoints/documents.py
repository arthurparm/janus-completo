from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request, Query, Form
from pydantic import BaseModel
from app.services.document_service import DocumentIngestionService
try:
    from prometheus_client import Counter, Histogram  # type: ignore
    _DOC_UPLOAD_REQ = Counter("doc_upload_requests_total", "Upload de documentos", ["status"])  # type: ignore
    _DOC_UPLOAD_LAT = Histogram("doc_upload_latency_seconds", "Latência de upload de documentos")  # type: ignore
    _DOC_SEARCH_REQ = Counter("doc_search_requests_total", "Busca de documentos", ["status"])  # type: ignore
    _DOC_SEARCH_LAT = Histogram("doc_search_latency_seconds", "Latência de busca de documentos")  # type: ignore
    _DOC_STATUS_REQ = Counter("doc_status_requests_total", "Consulta de status de documento", ["status"])  # type: ignore
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
from app.db.vector_store import get_qdrant_client, get_or_create_collection
from app.db.vector_store import get_collection_info
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.core.embeddings.embedding_manager import embed_text
from qdrant_client import models
from app.config import settings

router = APIRouter(tags=["Documents"])

def get_doc_service(request: Request) -> DocumentIngestionService:
    return request.app.state.document_service

class UploadResponse(BaseModel):
    doc_id: str
    chunks: int
    status: str
    consolidation: Optional[Dict[str, Any]] = None

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    request: Request = None,
    service: DocumentIngestionService = Depends(get_doc_service),
    auto_consolidate: Optional[bool] = Form(False),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
):
    import time as _t
    _t0 = _t.perf_counter()
    try:
        hdr_uid = request.headers.get("X-User-Id") if request else None
    except Exception:
        hdr_uid = None
    uid = user_id or hdr_uid
    if not uid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id necessário")
    data = await file.read()
    try:
        if len(data or b"") > int(getattr(settings, "DOCS_MAX_FILE_SIZE_BYTES", 10_000_000)):
            _DOC_UPLOAD_REQ.labels("file_too_large").inc()
            _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
            return UploadResponse(doc_id="", chunks=0, status="file_too_large", consolidation=None)
    except Exception:
        pass
    # Verifica quota de pontos por usuário antes de indexar
    try:
        info = get_collection_info(f"user_{uid}")
        points_count = int(info.get("points_count") or 0)
        # estima chunks a partir do tamanho do texto, aproximado após parsing; fallback para 1000 bytes/chunk
        est_chunks = max(1, int(len(data or b"") / 1000))
        if points_count + est_chunks > int(getattr(settings, "DOCS_MAX_POINTS_PER_USER", 50_000)):
            return UploadResponse(doc_id="", chunks=0, status="quota_exceeded", consolidation=None)
    except Exception:
        pass

    cm = (_tracer.start_as_current_span("docs.upload") if _OTEL else nullcontext())
    with cm:  # type: ignore
        result = await service.ingest_file(user_id=uid, filename=file.filename or "document", content_type=file.content_type or "", data=data)
    consolidation = None
    try:
        if bool(auto_consolidate):
            consolidation = await knowledge.consolidate_document(user_id=uid, doc_id=result.get("doc_id"), limit=50)
    except Exception:
        consolidation = None
    try:
        _DOC_UPLOAD_REQ.labels(str(result.get("status") or "indexed")).inc()
        _DOC_UPLOAD_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    except Exception:
        pass
    return UploadResponse(doc_id=result.get("doc_id"), chunks=result.get("chunks"), status=result.get("status"), consolidation=consolidation)

class DocSearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@router.get("/search", response_model=DocSearchResponse)
async def search_documents(
    query: str = Query(...),
    user_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    limit: int = 5,
    min_score: Optional[float] = None,
    request: Request = None,
):
    import time as _t
    _t0 = _t.perf_counter()
    try:
        hdr_uid = request.headers.get("X-User-Id") if request else None
    except Exception:
        hdr_uid = None
    uid = user_id or hdr_uid
    if not uid:
        _DOC_SEARCH_REQ.labels("error").inc()
        _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
        return DocSearchResponse(results=[])
    vec = embed_text(query)
    client = get_qdrant_client()
    collection_name = get_or_create_collection(f"user_{uid}")
    must: List[models.FieldCondition] = [
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=uid)),
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="doc_chunk")),
    ]
    if doc_id:
        must.append(models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id)))
    sc_filter = models.Filter(must=must)
    cm = (_tracer.start_as_current_span("docs.search") if _OTEL else nullcontext())
    with cm:  # type: ignore
        res = client.search(
        collection_name=collection_name,
        query_vector=vec,
        limit=limit,
        with_payload=True,
        query_filter=sc_filter,
        score_threshold=min_score if isinstance(min_score, float) else None,
    )
    results: List[Dict[str, Any]] = []
    for r in res:
        payload = r.payload or {}
        meta = payload.get("metadata", {})
        results.append({
            "id": r.id,
            "score": r.score,
            "doc_id": meta.get("doc_id"),
            "file_name": meta.get("file_name"),
            "index": meta.get("index"),
            "timestamp": meta.get("timestamp"),
        })
    try:
        _DOC_SEARCH_REQ.labels("success").inc()
        _DOC_SEARCH_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    except Exception:
        pass
    return DocSearchResponse(results=results)


class DocStatusResponse(BaseModel):
    doc_id: str
    user_id: str
    chunks_indexed: int
    samples: List[Dict[str, Any]]


@router.get("/status/{doc_id}", response_model=DocStatusResponse)
async def document_status(doc_id: str, user_id: Optional[str] = None, request: Request = None):
    import time as _t
    _t0 = _t.perf_counter()
    try:
        hdr_uid = request.headers.get("X-User-Id") if request else None
    except Exception:
        hdr_uid = None
    uid = user_id or hdr_uid
    if not uid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id necessário")
    client = get_qdrant_client()
    coll = get_or_create_collection(f"user_{uid}")
    try:
        qfilter = models.Filter(must=[models.FieldCondition(key="metadata.doc_id", match=models.MatchValue(value=doc_id))])
    except Exception:
        qfilter = None
    cm = (_tracer.start_as_current_span("docs.status") if _OTEL else nullcontext())
    with cm:  # type: ignore
        hits = client.search(collection_name=coll, query_vector=[0.0] * 1536, limit=10, with_payload=True, query_filter=qfilter)
    samples: List[Dict[str, Any]] = []
    for h in hits or []:
        payload = getattr(h, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        samples.append({
            "id": getattr(h, "id", None),
            "file_name": meta.get("file_name"),
            "index": meta.get("index"),
            "content": payload.get("content"),
        })
    try:
        cnt = client.count(collection_name=coll, count_filter=qfilter, exact=True)
        total = int(getattr(cnt, "count", 0) or 0)
    except Exception:
        total = len(samples)
    try:
        _DOC_STATUS_REQ.labels("success").inc()
        _DOC_STATUS_LAT.observe(max(0.0, _t.perf_counter() - _t0))
    except Exception:
        pass
    return DocStatusResponse(doc_id=doc_id, user_id=uid, chunks_indexed=total, samples=samples)