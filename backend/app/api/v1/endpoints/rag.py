import time
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.core.memory.rag_telemetry import confidence_from_scores, emit_step_telemetry
from app.core.routing import RouteIntent, RouteTarget, get_knowledge_routing_policy
from app.core.security.request_guard import resolve_user_scope_id
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


def _emit_rag_step(
    *,
    endpoint: str,
    step: str,
    source: str,
    db: str,
    started_at: float,
    scores: list[Any] | None = None,
    confidence: float | None = None,
    error_code: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    derived_confidence = confidence if confidence is not None else confidence_from_scores(scores or [])
    emit_step_telemetry(
        endpoint=endpoint,
        step=step,
        source=source,
        db=db,
        latency_ms=(time.perf_counter() - started_at) * 1000,
        confidence=derived_confidence,
        error_code=error_code,
        extra=extra,
    )


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
    error_code: str | None = None
    cm = _tracer.start_as_current_span("rag.search") if _OTEL else nullcontext()
    try:
        with cm:  # type: ignore
            results = await service.recall_filtered(
                query=query, filters=filters, limit=limit, min_score=min_score
            )
        _RAG_REQ.labels("search", "success").inc()
        _RAG_LAT.labels("search", "success").observe(max(0.0, _t.perf_counter() - _start))
    except Exception as e:
        _RAG_REQ.labels("search", "error").inc()
        _RAG_LAT.labels("search", "error").observe(max(0.0, _t.perf_counter() - _start))
        error_code = type(e).__name__
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
    _emit_rag_step(
        endpoint="/rag/search",
        step="retrieval",
        source="vector",
        db="qdrant",
        started_at=_start,
        scores=[r.get("score") for r in results if isinstance(r, dict)],
        error_code=error_code,
        extra={"result_count": len(results)},
    )

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

    started_at = time.perf_counter()
    # Async
    try:
        collection_name = await aget_or_create_collection(f"user_{user_id}")
        vec = await aembed_text(query)
    except Exception as e:
        # Fallback se falhar
        _emit_rag_step(
            endpoint="/rag/user-chat",
            step="retrieval",
            source="vector",
            db="qdrant",
            started_at=started_at,
            confidence=0.0,
            error_code=type(e).__name__,
        )
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
    error_code: str | None = None
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
    except Exception as e:
        _RAG_REQ.labels("user_chat", "error").inc()
        _RAG_LAT.labels("user_chat", "error").observe(max(0.0, _t.perf_counter() - _start))
        error_code = type(e).__name__
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
    _emit_rag_step(
        endpoint="/rag/user-chat",
        step="retrieval",
        source="vector",
        db="qdrant",
        started_at=_start,
        scores=[r.get("score") for r in items if isinstance(r, dict)],
        error_code=error_code,
        extra={"result_count": len(items)},
    )
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

    started_at = time.perf_counter()
    try:
        coll = await aget_or_create_collection(f"user_{user_id}")
        vec = await aembed_text(query)
    except Exception as e:
        _emit_rag_step(
            endpoint="/rag/productivity",
            step="retrieval",
            source="vector",
            db="qdrant",
            started_at=started_at,
            confidence=0.0,
            error_code=e.__class__.__name__,
        )
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
    error_code: str | None = None
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
    except Exception as e:
        _RAG_REQ.labels("productivity", "error").inc()
        _RAG_LAT.labels("productivity", "error").observe(max(0.0, _t.perf_counter() - _start))
        error_code = type(e).__name__
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
    _emit_rag_step(
        endpoint="/rag/productivity",
        step="retrieval",
        source="vector",
        db="qdrant",
        started_at=_start,
        scores=[r.get("score") for r in items if isinstance(r, dict)],
        error_code=error_code,
        extra={"result_count": len(items)},
    )
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
    started_at = time.perf_counter()
    user_id = resolve_user_scope_id(http, user_id)
    if not user_id:
        _emit_rag_step(
            endpoint="/rag/user_chat",
            step="retrieval",
            source="vector",
            db="qdrant",
            started_at=started_at,
            confidence=0.0,
            error_code="SKIPPED_MISSING_USER_ID",
        )
        return RAGUserChatResponseV2(results=[])

    try:
        vec = await aembed_text(query)
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(f"user_{user_id}")
    except Exception as e:
        _emit_rag_step(
            endpoint="/rag/user_chat",
            step="retrieval",
            source="vector",
            db="qdrant",
            started_at=started_at,
            confidence=0.0,
            error_code=type(e).__name__,
        )
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
    error_code: str | None = None
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
    except Exception as e:
        _RAG_REQ.labels("user_chat_v2", "error").inc()
        _RAG_LAT.labels("user_chat_v2", "error").observe(max(0.0, _t.perf_counter() - _start))
        error_code = type(e).__name__
        res = []
    try:
        _RAG_RESULTS_TOTAL.labels("user_chat_v2").inc(len(res or []))
        for r in (getattr(res, "points", res) or []):
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
    _emit_rag_step(
        endpoint="/rag/user_chat",
        step="retrieval",
        source="vector",
        db="qdrant",
        started_at=_start,
        scores=[r.get("score") for r in results if isinstance(r, dict)],
        error_code=error_code,
        extra={"result_count": len(results)},
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
    started_at = time.perf_counter()
    uid = resolve_user_scope_id(http, user_id)
    if not uid:
        _emit_rag_step(
            endpoint="/rag/hybrid_search",
            step="vector_retrieval",
            source="hybrid",
            db="qdrant+neo4j",
            started_at=started_at,
            confidence=0.0,
            error_code="SKIPPED_MISSING_USER_ID",
        )
        return RAGHybridResponse(answer="", citations=[])
    route_decision = get_knowledge_routing_policy().resolve(
        RouteIntent.RAG_HYBRID_SEARCH,
        user_id=uid,
        include_graph=True,
        query=query,
    )
    route_meta = {
        "route.rule_id": route_decision.rule_id,
        "route.primary": route_decision.primary.value,
        "route.fallback": route_decision.fallback,
    }
    route_targets = {route_decision.primary, *route_decision.secondary}
    vector_enabled = RouteTarget.QDRANT in route_targets
    graph_enabled = RouteTarget.NEO4J in route_targets

    import time as _t

    _start = _t.perf_counter()
    vector_error_code: str | None = None
    results_vec: list[dict[str, Any]] = []
    if vector_enabled:
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
        except Exception as e:
            _RAG_REQ.labels("hybrid", "error").inc()
            _RAG_LAT.labels("hybrid", "error").observe(max(0.0, _t.perf_counter() - _start))
            vector_error_code = type(e).__name__
            results_vec = []
    else:
        vector_error_code = "SKIPPED_BY_ROUTE_POLICY"
    try:
        _RAG_RESULTS_TOTAL.labels("hybrid").inc(len(results_vec))
        for r in results_vec:
            s = float(r.get("score", 0.0) or 0.0)
            _RAG_SCORES.labels("hybrid").observe(max(0.0, min(1.0, s)))
    except Exception:
        pass
    _emit_rag_step(
        endpoint="/rag/hybrid_search",
        step="vector_retrieval",
        source="vector",
        db="qdrant",
        started_at=_start,
        scores=[r.get("score") for r in results_vec if isinstance(r, dict)],
        error_code=vector_error_code,
        extra={"result_count": len(results_vec), **route_meta},
    )
    from app.db.graph import get_graph_db
    from app.repositories.knowledge_repository import KnowledgeRepository

    graph_start = time.perf_counter()
    graph_error_code: str | None = None
    concepts: list[dict[str, Any]] = []
    if graph_enabled:
        try:
            kr = KnowledgeRepository(await get_graph_db())
            concepts = await kr.find_related_concepts(concept=query, max_depth=2, limit=limit)
        except Exception as e:
            graph_error_code = type(e).__name__
            concepts = []
    else:
        graph_error_code = "SKIPPED_BY_ROUTE_POLICY"
    graph_scores: list[float] = []
    for c in concepts:
        try:
            graph_scores.append(1.0 / (1.0 + float(c.get("distance") or 1.0)))
        except Exception:
            continue
    _emit_rag_step(
        endpoint="/rag/hybrid_search",
        step="graph_retrieval",
        source="graph",
        db="neo4j",
        started_at=graph_start,
        scores=graph_scores,
        error_code=graph_error_code,
        extra={"result_count": len(concepts), **route_meta},
    )
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
