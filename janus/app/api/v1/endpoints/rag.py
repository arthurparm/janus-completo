from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.services.memory_service import MemoryService, get_memory_service

try:
    from prometheus_client import Counter, Histogram

    _RAG_REQ = Counter("rag_requests_total", "Total de requisições RAG", ["endpoint", "outcome"])  # type: ignore
    _RAG_LAT = Histogram(
        "rag_latency_seconds", "Latência por endpoint RAG", ["endpoint", "outcome"]
    )  # type: ignore
    _RAG_RESULTS_TOTAL = Counter(
        "rag_results_total", "Total de resultados retornados", ["endpoint"]
    )  # type: ignore
    _RAG_SCORES = Histogram("rag_search_scores", "Distribuição de scores de busca", ["endpoint"])  # type: ignore
except Exception:

    class _Noop:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    _RAG_REQ = _Noop()  # type: ignore
    _RAG_LAT = _Noop()  # type: ignore
    _RAG_RESULTS_TOTAL = _Noop()  # type: ignore
    _RAG_SCORES = _Noop()  # type: ignore
from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None

router = APIRouter(tags=["RAG"])


class RAGSearchResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]


@router.get(
    "/search",
    response_model=RAGSearchResponse,
    summary="Busca baseada em fatos com memória vetorial",
)
async def rag_search(
    query: str = Query(..., description="Pergunta ou texto de busca"),
    type: str | None = Query(None, description="Filtrar por tipo da experiência"),
    origin: str | None = Query(None, description="Filtrar por metadata.origin"),
    doc_id: str | None = Query(None, description="Filtrar por metadata.doc_id"),
    file_path: str | None = Query(None, description="Filtrar por metadata.file_path"),
    limit: int | None = Query(5, ge=1, le=10),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
    service: MemoryService = Depends(get_memory_service),
):
    filters: dict[str, Any] = {}
    if type is not None:
        filters["type"] = type
    if origin is not None:
        filters["origin"] = origin
    if doc_id is not None:
        filters["metadata.doc_id"] = doc_id
    if file_path is not None:
        filters["metadata.file_path"] = file_path
    # Evita duplicatas por padrão
    filters["status_not"] = "duplicate"

    import time as _t

    _start = _t.perf_counter()
    cm = _tracer.start_as_current_span("rag.search") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            results = await service.recall_filtered(
                query=query, filters=filters, limit=limit, min_score=min_score
            )
        _RAG_REQ.labels("search", "success").inc()
        _RAG_LAT.labels("search", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception:
        _RAG_REQ.labels("search", "error").inc()
        _RAG_LAT.labels("search", "error").observe(max(0.0, _t.perf_counter() - _start))
        results = []
    try:
        _RAG_RESULTS_TOTAL.labels("search").inc(len(results))
        for r in results:
            s = float(r.get("score", 0.0) or 0.0)
            _RAG_SCORES.labels("search").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass

    citations: list[dict[str, Any]] = []
    for r in results:
        meta = r.get("metadata") or {}
        citations.append(
            {
                "id": r.get("id"),
                "doc_id": meta.get("doc_id"),
                "file_path": meta.get("file_path"),
                "type": meta.get("type"),
                "origin": meta.get("origin"),
                "score": r.get("score"),
            }
        )

    snippets: list[str] = []
    for r in results:
        c = str(r.get("content") or "")
        if not c:
            continue
        snippets.append(c[:300])
        if len(snippets) >= max(1, min(3, limit or 5)):
            break

    if not snippets:
        answer = "Nenhum trecho relevante encontrado para a consulta."
    else:
        answer = "\n\n".join(snippets)

    return RAGSearchResponse(answer=answer, citations=citations)


class RAGUserChatResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]


@router.get(
    "/user-chat",
    response_model=RAGUserChatResponse,
    summary="Busca em mensagens pessoais indexadas por usuário",
)
async def rag_user_chat_search(
    query: str = Query(..., description="Pergunta ou texto de busca"),
    user_id: str = Query(..., description="ID do usuário"),
    session_id: str | None = Query(None, description="ID da conversa para filtrar"),
    role: str | None = Query(None, description="Filtrar por role (user|assistant)"),
    limit: int | None = Query(5, ge=1, le=10),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
):
    from qdrant_client import models

    # Async
    try:
        collection_name = await aget_or_create_collection(f"user_{user_id}")
        vec = await aembed_text(query)
    except Exception:
        # Fallback se falhar
        return RAGUserChatResponse(answer="Erro na busca.", citations=[])

    must: list[models.FieldCondition] = []
    if session_id:
        must.append(
            models.FieldCondition(
                key="metadata.session_id", match=models.MatchValue(value=session_id)
            )
        )
    if role:
        must.append(models.FieldCondition(key="metadata.role", match=models.MatchValue(value=role)))
    qfilter = models.Filter(must=must) if must else None

    client = get_async_qdrant_client()
    import time as _t

    _start = _t.perf_counter()
    cm = _tracer.start_as_current_span("rag.user_chat") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            res = await client.query_points(
                collection_name=collection_name,
                query=vec,
                limit=limit or 5,
                with_payload=True,
                query_filter=qfilter,
            )
        hits = getattr(res, "points", res) if "res" in locals() else []
        _RAG_REQ.labels("user_chat", "success").inc()
        _RAG_LAT.labels("user_chat", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception:
        _RAG_REQ.labels("user_chat", "error").inc()
        _RAG_LAT.labels("user_chat", "error").observe(max(0.0, _t.perf_counter() - _start))
        hits = []
    try:
        _RAG_RESULTS_TOTAL.labels("user_chat").inc(len(hits or []))
        for h in hits or []:
            s = float(getattr(h, "score", 0.0) or 0.0)
            _RAG_SCORES.labels("user_chat").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass

    items: list[dict[str, Any]] = []
    for h in hits or []:
        payload = getattr(h, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        content = payload.get("content") or ""
        score = float(getattr(h, "score", 0.0) or 0.0)
        if min_score is not None and score < float(min_score):
            continue
        items.append(
            {
                "id": getattr(h, "id", None),
                "content": content,
                "metadata": meta,
                "score": score,
            }
        )

    citations: list[dict[str, Any]] = []
    for r in items:
        m = r.get("metadata") or {}
        citations.append(
            {
                "id": r.get("id"),
                "user_id": m.get("user_id"),
                "session_id": m.get("session_id"),
                "role": m.get("role"),
                "score": r.get("score"),
            }
        )

    snippets: list[str] = []
    for r in items:
        c = str(r.get("content") or "")
        if not c:
            continue
        snippets.append(c[:300])
        if len(snippets) >= max(1, min(3, limit or 5)):
            break

    answer = "Nenhum trecho relevante encontrado." if not snippets else "\n\n".join(snippets)
    return RAGUserChatResponse(answer=answer, citations=citations)


class RAGProductivityResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]


@router.get(
    "/productivity",
    response_model=RAGProductivityResponse,
    summary="Busca em itens de produtividade (calendar/mail/notes) do usuário",
)
async def rag_productivity_search(
    query: str = Query(..., description="Consulta"),
    user_id: str = Query(..., description="ID do usuário"),
    type: str | None = Query(None, description="calendar_event|email_message|note_item"),
    limit: int | None = Query(5, ge=1, le=10),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
):
    from qdrant_client import models

    try:
        coll = await aget_or_create_collection(f"user_{user_id}")
        vec = await aembed_text(query)
    except Exception:
        return RAGProductivityResponse(answer="Erro em serviços.", citations=[])

    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=user_id))
    ]
    if type:
        must.append(models.FieldCondition(key="metadata.type", match=models.MatchValue(value=type)))
    # Evitar pontos marcados como duplicados
    must_not: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.status", match=models.MatchValue(value="duplicate"))
    ]
    qfilter = (
        models.Filter(must=must, must_not=must_not) if must else models.Filter(must_not=must_not)
    )

    client = get_async_qdrant_client()
    import time as _t

    _start = _t.perf_counter()
    cm = _tracer.start_as_current_span("rag.productivity") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            res = await client.query_points(
                collection_name=coll,
                query=vec,
                limit=limit or 5,
                with_payload=True,
                query_filter=qfilter,
            )
        hits = getattr(res, "points", res) if "res" in locals() else []
        _RAG_REQ.labels("productivity", "success").inc()
        _RAG_LAT.labels("productivity", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception:
        _RAG_REQ.labels("productivity", "error").inc()
        _RAG_LAT.labels("productivity", "error").observe(max(0.0, _t.perf_counter() - _start))
        hits = []
    try:
        _RAG_RESULTS_TOTAL.labels("productivity").inc(len(hits or []))
        for h in hits or []:
            s = float(getattr(h, "score", 0.0) or 0.0)
            _RAG_SCORES.labels("productivity").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass

    items: list[dict[str, Any]] = []
    for h in hits or []:
        payload = getattr(h, "payload", {}) or {}
        meta = payload.get("metadata") or {}
        content = payload.get("content") or ""
        score = float(getattr(h, "score", 0.0) or 0.0)
        if min_score is not None and score < float(min_score):
            continue
        items.append(
            {
                "id": getattr(h, "id", None),
                "content": content,
                "metadata": meta,
                "score": score,
            }
        )

    citations: list[dict[str, Any]] = []
    for r in items:
        m = r.get("metadata") or {}
        citations.append(
            {
                "id": r.get("id"),
                "type": m.get("type"),
                "user_id": m.get("user_id"),
                "score": r.get("score"),
            }
        )

    snippets: list[str] = []
    for r in items:
        c = str(r.get("content") or "")
        if not c:
            continue
        snippets.append(c[:300])
        if len(snippets) >= max(1, min(3, limit or 5)):
            break

    answer = "Nenhum item relevante encontrado." if not snippets else "\n\n".join(snippets)
    return RAGProductivityResponse(answer=answer, citations=citations)


class RAGUserChatResponseV2(BaseModel):
    results: list[dict[str, Any]]


@router.get(
    "/user_chat",
    response_model=RAGUserChatResponseV2,
    summary="Busca semântica em mensagens pessoais de chat",
    name="user_chat_v2",  # Avoid duplicate name
)
async def rag_user_chat_search_v2(
    query: str,
    user_id: str | None = None,
    session_id: str | None = None,
    start_ts_ms: int | None = None,
    end_ts_ms: int | None = None,
    limit: int = 5,
    min_score: float | None = None,
    http: Request = None,
):
    if not user_id:
        try:
            user_id = http.headers.get("X-User-Id") if http else None
        except Exception:
            user_id = None
    if not user_id:
        return RAGUserChatResponseV2(results=[])

    try:
        vec = await aembed_text(query)
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(f"user_{user_id}")
    except Exception:
        return RAGUserChatResponseV2(results=[])

    # Filtro por payload
    must: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.user_id", match=models.MatchValue(value=user_id))
    ]
    if session_id:
        must.append(
            models.FieldCondition(
                key="metadata.session_id", match=models.MatchValue(value=session_id)
            )
        )
    # Apenas pontos de chat
    must.append(
        models.FieldCondition(key="metadata.type", match=models.MatchValue(value="chat_msg"))
    )
    if isinstance(start_ts_ms, int) or isinstance(end_ts_ms, int):
        rng = {}
        if isinstance(start_ts_ms, int):
            rng["gte"] = start_ts_ms
        if isinstance(end_ts_ms, int):
            rng["lte"] = end_ts_ms
        must.append(models.FieldCondition(key="metadata.timestamp", range=models.Range(**rng)))
    must_not_uc: list[models.FieldCondition] = [
        models.FieldCondition(key="metadata.status", match=models.MatchValue(value="duplicate"))
    ]
    sc_filter = models.Filter(must=must, must_not=must_not_uc)
    import time as _t

    _start = _t.perf_counter()
    cm = _tracer.start_as_current_span("rag.user_chat_v2") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            res = await client.query_points(
                collection_name=collection_name,
                query=vec,
                limit=limit,
                with_payload=True,
                query_filter=sc_filter,
                score_threshold=min_score if isinstance(min_score, float) else None,
            )
        _RAG_REQ.labels("user_chat_v2", "success").inc()
        _RAG_LAT.labels("user_chat_v2", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception:
        _RAG_REQ.labels("user_chat_v2", "error").inc()
        _RAG_LAT.labels("user_chat_v2", "error").observe(max(0.0, _t.perf_counter() - _start))
        res = []
    try:
        _RAG_RESULTS_TOTAL.labels("user_chat_v2").inc(len(res or []))
        for r in getattr(res, "points", res) or []:
            s = float(getattr(r, "score", 0.0) or 0.0)
            _RAG_SCORES.labels("user_chat_v2").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass
    points = getattr(res, "points", res) or []
    results: list[dict[str, Any]] = []
    for r in points:
        payload = r.payload or {}
        meta = payload.get("metadata", {})
        results.append(
            {
                "id": r.id,
                "score": r.score,
                "role": meta.get("role"),
                "session_id": meta.get("session_id"),
                "timestamp": meta.get("timestamp"),
            }
        )
    return RAGUserChatResponseV2(results=results)


class RAGHybridResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]


@router.get(
    "/hybrid_search",
    response_model=RAGHybridResponse,
    summary="Busca híbrida (vetor + grafo) em conhecimento pessoal",
)
async def rag_hybrid_search(
    query: str,
    user_id: str | None = None,
    limit: int = 5,
    min_score: float | None = None,
    http: Request = None,
    service: MemoryService = Depends(get_memory_service),
):
    try:
        hdr_uid = http.headers.get("X-User-Id") if http else None
    except Exception:
        hdr_uid = None
    uid = user_id or hdr_uid
    if not uid:
        return RAGHybridResponse(answer="", citations=[])

    import time as _t

    _start = _t.perf_counter()
    cm = _tracer.start_as_current_span("rag.hybrid") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            # Exclui duplicados na busca vetorial híbrida
            results_vec = await service.recall_filtered(
                query=query,
                filters={"metadata.user_id": uid, "status_not": "duplicate"},
                limit=limit,
                min_score=min_score,
            )
        _RAG_REQ.labels("hybrid", "success").inc()
        _RAG_LAT.labels("hybrid", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception:
        _RAG_REQ.labels("hybrid", "error").inc()
        _RAG_LAT.labels("hybrid", "error").observe(max(0.0, _t.perf_counter() - _start))
        results_vec = []
    try:
        _RAG_RESULTS_TOTAL.labels("hybrid").inc(len(results_vec))
        for r in results_vec:
            s = float(r.get("score", 0.0) or 0.0)
            _RAG_SCORES.labels("hybrid").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass
    from app.db.graph import get_graph_db
    from app.repositories.knowledge_repository import KnowledgeRepository

    kr = KnowledgeRepository(await get_graph_db())
    concepts = await kr.find_related_concepts(concept=query, max_depth=2, limit=limit)
    citations: list[dict[str, Any]] = []
    for r in results_vec:
        meta = r.get("metadata") or {}
        citations.append(
            {
                "source": "vector",
                "score": r.get("score"),
                "type": meta.get("type"),
                "id": r.get("id"),
                "doc_id": meta.get("doc_id"),
                "file_path": meta.get("file_path"),
                "origin": meta.get("origin"),
            }
        )
    for c in concepts:
        citations.append(
            {
                "source": "graph",
                "concept": c.get("concept"),
                "relationship": c.get("relationship"),
                "distance": c.get("distance"),
            }
        )
    from app.config import settings

    wv = float(getattr(settings, "RAG_HYBRID_VECTOR_WEIGHT", 0.7))
    wg = float(getattr(settings, "RAG_HYBRID_GRAPH_WEIGHT", 0.3))

    def _score_vec(r: dict[str, Any]) -> float:
        try:
            s = float(r.get("score") or 0.0)
            return wv * max(0.0, min(1.0, s))
        except Exception:
            return 0.0

    def _score_concept(c: dict[str, Any]) -> float:
        try:
            d = float(c.get("distance") or 1.0)
            return wg * max(0.0, 1.0 / (1.0 + d))
        except Exception:
            return 0.0

    merged: list[dict[str, Any]] = []
    for r in results_vec:
        merged.append(
            {"type": "vector", "content": str(r.get("content") or ""), "score": _score_vec(r)}
        )
    for c in concepts:
        merged.append(
            {
                "type": "graph",
                "content": f"Related concept: {c.get('concept')} via {c.get('relationship')}",
                "score": _score_concept(c),
            }
        )
    merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    snippets: list[str] = []
    for m in merged[: max(1, min(3, limit))]:
        t = str(m.get("content") or "")
        if t:
            snippets.append(t[:300])
    answer = "\n\n".join(snippets) if snippets else "Nenhum trecho relevante encontrado."
    return RAGHybridResponse(answer=answer, citations=citations)
