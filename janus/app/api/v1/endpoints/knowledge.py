from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.knowledge import CodeEntity
from app.services.knowledge_service import KnowledgeService, get_knowledge_service

router = APIRouter(tags=["Knowledge"])
logger = structlog.get_logger(__name__)


class IndexResponse(BaseModel):
    message: str
    summary: str


class KnowledgeQueryResponse(BaseModel):
    answer: str


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
        "both", regex=r"^(out|in|both)$", description="Direção do relacionamento (out/in/both)"
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
        from app.core.memory.memory_core import reset_memory_circuit_breaker

        await reset_memory_circuit_breaker()
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
            if detailed_status["system_health"]["is_healthy"]
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
