from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.security.request_guard import resolve_user_scope_id
from app.models.knowledge import CodeEntity
from app.services.knowledge_space_service import (
    KnowledgeSpaceService,
    get_knowledge_space_service,
)
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.core.workers.async_consolidation_worker import publish_consolidation_task

router = APIRouter(tags=["Knowledge"])
logger = structlog.get_logger(__name__)


class IndexResponse(BaseModel):
    message: str
    summary: str


class KnowledgeQueryResponse(BaseModel):
    answer: str


class CodeCitation(BaseModel):
    type: str
    name: str
    file_path: str
    line: int
    full_name: str
    relevance: int


class CodeQuestionRequest(BaseModel):
    question: str
    limit: int | None = 10
    citation_limit: int | None = 8


class CodeQuestionResponse(BaseModel):
    answer: str
    citations: list[CodeCitation]


class RelatedConceptsRequest(BaseModel):
    concept: str
    max_depth: int = 2
    limit: int = 10
    skip: int = 0


class RelatedConceptItem(BaseModel):
    concept: str
    relationship: str
    distance: int


class RelatedConceptsResponse(BaseModel):
    results: list[RelatedConceptItem]


class ReindexRequest(BaseModel):
    batch_size: int = 50
    labels: list[str] | None = None


class ReindexResponse(BaseModel):
    status: str
    updated_count: int


class EntityRelationshipsItem(BaseModel):
    related_entity: str
    related_type: str
    relationship: str
    distance: int


class EntityRelationshipsResponse(BaseModel):
    results: list[EntityRelationshipsItem]


class ClearGraphResponse(BaseModel):
    status: str
    message: str
    remaining_nodes: int


# --- Sprint 8 DTOs ---


class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: int | None = 10  # Usado pelo pipeline Graph RAG para limitar contexto


class KnowledgeHealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    qdrant_connected: bool
    circuit_breaker_open: bool
    total_nodes: int
    total_relationships: int


class ConsolidationRequest(BaseModel):
    mode: str = "batch"  # "batch" ou "single"
    limit: int = 10
    min_score: float = 0.0
    experience_id: str | None = None
    experience_content: str | None = None
    metadata: dict[str, Any] | None = None


class ConsolidationResponse(BaseModel):
    message: str
    stats: dict[str, Any]


class KnowledgeSpaceCreateRequest(BaseModel):
    name: str
    user_id: str | None = None
    source_type: str = "documentation"
    source_id: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    description: str | None = None


class KnowledgeSpaceResponse(BaseModel):
    knowledge_space_id: str
    user_id: str
    name: str
    source_type: str
    source_id: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    description: str | None = None
    consolidation_status: str
    consolidation_summary: str | None = None
    last_consolidated_at: str | None = None
    sections_total: int = 0
    sections_indexed: int = 0
    sections_skipped_as_noise: int = 0
    canonical_frames_total: int = 0
    consolidation_quality_score: float = 0.0


class KnowledgeSpaceStatusResponse(KnowledgeSpaceResponse):
    documents_total: int = 0
    documents_indexed: int = 0
    documents_processing: int = 0
    documents_queued: int = 0
    documents_failed: int = 0
    chunks_total: int = 0
    chunks_indexed: int = 0
    progress: float = 0.0


class KnowledgeSpaceListResponse(BaseModel):
    items: list[KnowledgeSpaceResponse]


class AttachDocumentRequest(BaseModel):
    user_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    doc_role: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None


class KnowledgeSpaceConsolidationRequest(BaseModel):
    user_id: str | None = None
    limit_docs: int = 20


class KnowledgeSpaceQueryRequest(BaseModel):
    user_id: str | None = None
    question: str
    mode: str = "auto"
    limit: int = 5


class KnowledgeSpaceQueryResponse(BaseModel):
    answer: str
    mode_used: str
    base_used: str
    answer_strategy: str = "scope"
    estimated_wait_seconds: int = 0
    estimated_wait_range_seconds: list[int] = []
    processing_profile: str | None = None
    processing_notice: str | None = None
    evidence_count: int = 0
    source_roles_used: list[str] = []
    source_scope: dict[str, Any]
    citations: list[dict[str, Any]]
    confidence: float
    gaps_or_conflicts: list[str]


# --- Endpoints ---


@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código")
async def trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.index_codebase()


@router.get("/stats", summary="Estatísticas do grafo")
async def get_knowledge_stats(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.get_stats()


@router.get("/entities", response_model=list[CodeEntity], summary="Lista entidades de código")
async def get_code_entities(
    file_path: str | None = Query(None, description="Filtra por caminho de arquivo."),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return await service.get_code_entities(file_path)


@router.get(
    "/entity/{entity_name}/relationships",
    response_model=EntityRelationshipsResponse,
    summary="Navega relacionamentos de uma entidade",
)
async def get_entity_relationships(
    entity_name: str,
    rel_type: str | None = Query(None, description="Filtra pelo tipo de relacionamento"),
    direction: str = Query(
        "both", pattern=r"^(out|in|both)$", description="Direção do relacionamento (out/in/both)"
    ),
    max_depth: int = Query(1, ge=1, le=5, description="Profundidade máxima de navegação"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    skip: int = Query(0, ge=0, description="Offset para paginação"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_entity_relationships(
        entity_name=entity_name,
        rel_type=rel_type,
        direction=direction,
        max_depth=max_depth,
        limit=limit,
        skip=skip,
    )
    items = [EntityRelationshipsItem(**row) for row in rows]
    return EntityRelationshipsResponse(results=items)


@router.delete("/clear", response_model=ClearGraphResponse, summary="Limpa todo o grafo")
async def clear_knowledge_graph(service: KnowledgeService = Depends(get_knowledge_service)):
    remaining_nodes = await service.clear_graph()
    return {
        "status": "success",
        "message": "Grafo de conhecimento limpo com sucesso",
        "remaining_nodes": remaining_nodes,
    }


# --- Sprint 8 Endpoints ---


@router.post(
    "/query",
    response_model=KnowledgeQueryResponse,
    summary="Consulta o grafo de conhecimento (Graph RAG)",
)
async def query_knowledge(
    request: KnowledgeQueryRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    answer = await service.semantic_query(request.query, limit=request.limit)
    return KnowledgeQueryResponse(answer=answer)


@router.post(
    "/query/code",
    response_model=CodeQuestionResponse,
    summary="Pergunta sobre codigo com citacoes de arquivo e linha",
)
async def query_code_with_citations(
    request: CodeQuestionRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    result = await service.ask_code_with_citations(
        question=request.question, limit=request.limit, citation_limit=request.citation_limit
    )
    citations = [CodeCitation(**row) for row in result.get("citations", [])]
    answer = result.get("answer", "")
    if not citations:
        answer = (
            "Nao encontrei citacoes rastreaveis para responder com seguranca sobre codigo. "
            "Reformule a pergunta ou indexe/reindexe a base."
        )
    return CodeQuestionResponse(answer=answer, citations=citations)


@router.post(
    "/concepts/related",
    response_model=RelatedConceptsResponse,
    summary="Busca conceitos relacionados",
)
async def related_concepts(
    request: RelatedConceptsRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    results = await service.find_related_concepts(
        concept=request.concept, max_depth=request.max_depth, limit=request.limit, skip=request.skip
    )
    items = [RelatedConceptItem(**row) for row in results]
    return RelatedConceptsResponse(results=items)


@router.post(
    "/concepts/reindex",
    response_model=ReindexResponse,
    summary="Reindexa (gera embeddings) para conceitos que ainda não possuem",
    description="Útil após migrações ou inserções em massa. Processa em lotes.",
)
async def reindex_concepts(
    request: ReindexRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    count = await service.reindex_graph(batch_size=request.batch_size, labels=request.labels)
    return ReindexResponse(status="success", updated_count=count)


class NodeTypesResponse(BaseModel):
    types: list[str]


@router.get(
    "/node-types", response_model=NodeTypesResponse, summary="Lista tipos de nós presentes no grafo"
)
async def get_node_types(service: KnowledgeService = Depends(get_knowledge_service)):
    types = await service.get_node_types()
    return NodeTypesResponse(types=types)


@router.get(
    "/health", response_model=KnowledgeHealthResponse, summary="Health check da memória semântica"
)
async def knowledge_health(service: KnowledgeService = Depends(get_knowledge_service)):
    health = await service.get_health_status()
    return KnowledgeHealthResponse(**health)


@router.post("/health/reset-circuit-breaker", summary="Reseta o circuit breaker do Qdrant")
async def reset_circuit_breaker():
    """
    Reseta o circuit breaker do Qdrant manualmente.
    Útil quando o Qdrant recupera após falhas temporárias.
    """
    try:
        from app.core.memory.memory_core import get_memory_db

        memory_db = await get_memory_db()
        memory_db.reset_circuit_breaker()
        return {"message": "Circuit breaker resetado com sucesso"}
    except Exception as e:
        logger.error("Erro ao resetar circuit breaker", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erro ao resetar circuit breaker: {e!s}")


@router.get("/health/detailed", summary="Status detalhado do sistema de memória")
async def detailed_health_check(service: KnowledgeService = Depends(get_knowledge_service)):
    """
    Retorna status detalhado incluindo circuit breaker, Qdrant e métricas de saúde.
    """
    try:
        # Get basic health from knowledge service
        basic_health = await service.get_health_status()

        # Get detailed circuit breaker status
        from app.core.memory.memory_core import get_memory_db

        memory_db = await get_memory_db()
        detailed_status = memory_db.get_circuit_breaker_status()

        # Get monitoring service status if available
        from app.core.memory.qdrant_monitoring import get_qdrant_monitoring_service

        monitoring_service = get_qdrant_monitoring_service()
        monitoring_status = (
            monitoring_service.get_detailed_metrics() if monitoring_service else None
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy"
            if not detailed_status.get("circuit_breaker_open", False) and not detailed_status.get("offline", False)
            else "degraded",
            "basic_health": basic_health,
            "detailed_status": detailed_status,
            "monitoring": monitoring_status,
            "recommendations": detailed_status.get("recommendations", []),
        }

    except Exception as e:
        logger.error("Erro ao obter status detalhado", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erro ao obter status detalhado: {e!s}")


@router.post(
    "/consolidate",
    response_model=ConsolidationResponse,
    summary="Dispara consolidação de conhecimento via fila",
)
async def publish_consolidation(request: ConsolidationRequest):
    # Publica tarefa para o worker de consolidação consumir
    from app.core.workers.async_consolidation_worker import publish_consolidation_task

    payload = request.model_dump()
    result = await publish_consolidation_task(payload)
    return ConsolidationResponse(message="Tarefa de consolidação publicada.", stats=result)


class DocConsolidationRequest(BaseModel):
    user_id: str
    doc_id: str
    limit: int = 50


@router.post(
    "/consolidate/document",
    response_model=ConsolidationResponse,
    summary="Consolida conhecimento a partir de um documento (doc_id) do usuário",
)
async def consolidate_document(
    request: DocConsolidationRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    stats = await service.consolidate_document(
        user_id=request.user_id, doc_id=request.doc_id, limit=request.limit
    )
    return ConsolidationResponse(message="Consolidação de documento concluída.", stats=stats)


class RegisterRelTypeRequest(BaseModel):
    name: str


class RegisterRelTypeResponse(BaseModel):
    status: str
    name: str


@router.post(
    "/relationship-types/register",
    response_model=RegisterRelTypeResponse,
    summary="Registra um tipo canônico de relacionamento",
)
async def register_relationship_type(
    request: RegisterRelTypeRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    res = await service.register_relationship_type(request.name)
    return RegisterRelTypeResponse(**res)


class QuarantineItem(BaseModel):
    reason: str | None
    type: str | None
    from_name: str | None
    to_name: str | None
    experience_id: str | None
    timestamp: str | None


class QuarantineListResponse(BaseModel):
    items: list[QuarantineItem]


@router.get(
    "/quarantine",
    response_model=QuarantineListResponse,
    summary="Lista itens em quarentena no grafo",
)
async def list_quarantine(
    limit: int = 50, service: KnowledgeService = Depends(get_knowledge_service)
):
    rows = await service.list_quarantine_items(limit=limit)
    items = [QuarantineItem(**row) for row in rows]
    return QuarantineListResponse(items=items)


class PromoteQuarantineRequest(BaseModel):
    from_name: str
    to_name: str
    type: str
    source_experience: str


class PromoteQuarantineResponse(BaseModel):
    status: str
    from_name: str
    to_name: str
    type: str


@router.post(
    "/quarantine/promote",
    response_model=PromoteQuarantineResponse,
    summary="Promove um item de quarentena a relacionamento no grafo",
)
async def promote_quarantine(
    request: PromoteQuarantineRequest, service: KnowledgeService = Depends(get_knowledge_service)
):
    res = await service.promote_quarantine_relationship(
        from_name=request.from_name,
        to_name=request.to_name,
        rel_type=request.type,
        source_experience=request.source_experience,
    )
    return PromoteQuarantineResponse(
        status=res.get("status"),
        from_name=request.from_name,
        to_name=request.to_name,
        type=request.type,
    )


@router.get(
    "/functions/calling",
    response_model=list[CodeEntity],
    summary="Lista funções que chamam a função informada",
)
async def functions_calling(
    name: str = Query(..., description="Nome da função alvo"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_functions_calling(function_name=name)
    return [CodeEntity(**row) for row in rows]


@router.get(
    "/files/importing",
    response_model=list[CodeEntity],
    summary="Lista arquivos que importam o módulo/arquivo informado",
)
async def files_importing(
    module: str = Query(..., description="Nome do módulo ou caminho do arquivo"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_files_importing(module=module)
    return [CodeEntity(**row) for row in rows]


@router.get(
    "/classes/implementations",
    response_model=list[CodeEntity],
    summary="Lista classes que implementam o protocolo/interface informado",
)
async def classes_implementations(
    protocol: str = Query(..., description="Nome do protocolo/interface"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    rows = await service.get_classes_implementing(protocol=protocol)
    return [CodeEntity(**row) for row in rows]


@router.post(
    "/spaces",
    response_model=KnowledgeSpaceResponse,
    summary="Cria um knowledge space isolado por obra/coleção",
)
async def create_knowledge_space(
    payload: KnowledgeSpaceCreateRequest,
    request: Request,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    user_id = resolve_user_scope_id(request, payload.user_id)
    if not user_id:
        raise HTTPException(
            status_code=422,
            detail="user_id necessário",
        )
    row = service.create_space(
        user_id=str(user_id),
        name=payload.name,
        source_type=payload.source_type,
        source_id=payload.source_id,
        edition_or_version=payload.edition_or_version,
        language=payload.language,
        parent_collection_id=payload.parent_collection_id,
        description=payload.description,
    )
    return KnowledgeSpaceResponse(**row)


@router.get(
    "/spaces",
    response_model=KnowledgeSpaceListResponse,
    summary="Lista knowledge spaces do usuário",
)
async def list_knowledge_spaces(
    request: Request,
    user_id: str | None = None,
    limit: int = 100,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    resolved_user_id = resolve_user_scope_id(request, user_id)
    if not resolved_user_id:
        raise HTTPException(status_code=422, detail="user_id necessário")
    rows = service.list_spaces(user_id=str(resolved_user_id), limit=limit)
    return KnowledgeSpaceListResponse(items=[KnowledgeSpaceResponse(**row) for row in rows])


@router.get(
    "/spaces/{knowledge_space_id}",
    response_model=KnowledgeSpaceStatusResponse,
    summary="Retorna status e progresso de um knowledge space",
)
async def get_knowledge_space_status(
    knowledge_space_id: str,
    request: Request,
    user_id: str | None = None,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    resolved_user_id = resolve_user_scope_id(request, user_id)
    if not resolved_user_id:
        raise HTTPException(status_code=422, detail="user_id necessário")
    row = service.get_space_status(
        knowledge_space_id=knowledge_space_id,
        user_id=str(resolved_user_id),
    )
    return KnowledgeSpaceStatusResponse(**row)


@router.post(
    "/spaces/{knowledge_space_id}/documents/{doc_id}/attach",
    response_model=dict,
    summary="Associa um documento existente a um knowledge space",
)
async def attach_document_to_space(
    knowledge_space_id: str,
    doc_id: str,
    payload: AttachDocumentRequest,
    request: Request,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    user_id = resolve_user_scope_id(request, payload.user_id)
    if not user_id:
        raise HTTPException(status_code=422, detail="user_id necessário")
    row = await service.attach_document(
        knowledge_space_id=knowledge_space_id,
        doc_id=doc_id,
        user_id=str(user_id),
        source_type=payload.source_type,
        source_id=payload.source_id,
        doc_role=payload.doc_role,
        edition_or_version=payload.edition_or_version,
        language=payload.language,
        parent_collection_id=payload.parent_collection_id,
    )
    return {"status": "ok", "document": row}


@router.post(
    "/spaces/{knowledge_space_id}/consolidate",
    response_model=ConsolidationResponse,
    summary="Consolida estruturalmente um knowledge space",
)
async def consolidate_knowledge_space(
    knowledge_space_id: str,
    payload: KnowledgeSpaceConsolidationRequest,
    request: Request,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    user_id = resolve_user_scope_id(request, payload.user_id)
    if not user_id:
        raise HTTPException(status_code=422, detail="user_id necessário")
    service.mark_consolidation_requested(knowledge_space_id=knowledge_space_id, user_id=str(user_id))
    stats = await publish_consolidation_task(
        {
            "mode": "knowledge_space",
            "knowledge_space_id": knowledge_space_id,
            "user_id": str(user_id),
            "limit_docs": payload.limit_docs,
        },
        correlation_id=knowledge_space_id,
    )
    stats["status_url"] = f"/api/v1/knowledge/spaces/{knowledge_space_id}?user_id={user_id}"
    return ConsolidationResponse(message="Consolidação estrutural publicada.", stats=stats)


@router.post(
    "/spaces/{knowledge_space_id}/query",
    response_model=KnowledgeSpaceQueryResponse,
    summary="Consulta knowledge space com fallback canônico para chunk_only",
)
async def query_knowledge_space(
    knowledge_space_id: str,
    payload: KnowledgeSpaceQueryRequest,
    request: Request,
    service: KnowledgeSpaceService = Depends(get_knowledge_space_service),
):
    user_id = resolve_user_scope_id(request, payload.user_id)
    if not user_id:
        raise HTTPException(status_code=422, detail="user_id necessário")
    result = await service.query_space(
        knowledge_space_id=knowledge_space_id,
        user_id=str(user_id),
        question=payload.question,
        mode=payload.mode,
        limit=payload.limit,
    )
    return KnowledgeSpaceQueryResponse(**result)
