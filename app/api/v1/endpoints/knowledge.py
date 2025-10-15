from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel
import structlog

from app.services.knowledge_service import KnowledgeService, get_knowledge_service

router = APIRouter(tags=["Knowledge"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---
class IndexResponse(BaseModel):
    message: str
    summary: str

class CodeEntity(BaseModel):
    type: str
    name: str
    file_path: str

class EntityDetailsResponse(BaseModel):
    entity: Dict[str, Any]
    relationships: List[Dict[str, Any]]

class ClearGraphResponse(BaseModel):
    status: str
    message: str
    remaining_nodes: int


# --- Sprint 8 DTOs ---

class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10  # Aceito mas não utilizado no pipeline atual


class KnowledgeQueryResponse(BaseModel):
    answer: str


class RelatedConceptsRequest(BaseModel):
    concept: str
    max_depth: int = 2


class RelatedConceptItem(BaseModel):
    concept: str
    relationship: Optional[str] = None
    distance: Optional[int] = None


class RelatedConceptsResponse(BaseModel):
    results: List[RelatedConceptItem]


class EntityDetailsRequest(BaseModel):
    entity_name: str


class NodeTypesResponse(BaseModel):
    types: List[str]


class KnowledgeHealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    total_nodes: int
    total_relationships: int


class ConsolidationRequest(BaseModel):
    limit: int = 10
    batch_size: Optional[int] = 10  # Placeholder, não utilizado diretamente


class ConsolidationResponse(BaseModel):
    message: str
    stats: Dict[str, Any]

# --- Endpoints ---

@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código")
async def trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.index_codebase()


@router.post("/consolidate", response_model=ConsolidationResponse, summary="Inicia a consolidação de experiências")
async def trigger_consolidation(request: ConsolidationRequest,
                                service: KnowledgeService = Depends(get_knowledge_service)):
    stats = await service.trigger_consolidation(limit=request.limit)
    return {"message": "Consolidação da memória semântica iniciada", "stats": stats}

@router.get("/stats", summary="Estatísticas do grafo")
async def get_knowledge_stats(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.get_stats()

@router.get("/entities", response_model=List[CodeEntity], summary="Lista entidades de código")
async def get_code_entities(
        file_path: Optional[str] = Query(None, description="Filtra por caminho de arquivo."),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    return await service.get_code_entities(file_path)

@router.get("/entity/{entity_name}", response_model=EntityDetailsResponse, summary="Obtém detalhes de uma entidade")
async def get_entity_details(entity_name: str, service: KnowledgeService = Depends(get_knowledge_service)):
    details = await service.get_entity_details(entity_name)
    if not details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entidade '{entity_name}' não encontrada.")
    return details

@router.delete("/clear", response_model=ClearGraphResponse, summary="Limpa todo o grafo")
async def clear_knowledge_graph(service: KnowledgeService = Depends(get_knowledge_service)):
    remaining_nodes = await service.clear_graph()
    return {
        "status": "success",
        "message": "Grafo de conhecimento limpo com sucesso",
        "remaining_nodes": remaining_nodes
    }


# --- Sprint 8 Endpoints ---

@router.post("/query", response_model=KnowledgeQueryResponse, summary="Consulta o grafo de conhecimento (Graph RAG)")
async def query_knowledge(request: KnowledgeQueryRequest, service: KnowledgeService = Depends(get_knowledge_service)):
    answer = await service.semantic_query(request.query)
    return KnowledgeQueryResponse(answer=answer)


@router.post("/concepts/related", response_model=RelatedConceptsResponse, summary="Busca conceitos relacionados")
async def related_concepts(request: RelatedConceptsRequest, service: KnowledgeService = Depends(get_knowledge_service)):
    results = await service.find_related_concepts(concept=request.concept, max_depth=request.max_depth)
    items = [RelatedConceptItem(**row) for row in results]
    return RelatedConceptsResponse(results=items)


@router.post("/entity/details", response_model=EntityDetailsResponse, summary="Obtém detalhes de uma entidade")
async def post_entity_details(request: EntityDetailsRequest,
                              service: KnowledgeService = Depends(get_knowledge_service)):
    details = await service.get_entity_details(request.entity_name)
    if not details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Entidade '{request.entity_name}' não encontrada.")
    return details


@router.get("/node-types", response_model=NodeTypesResponse, summary="Lista tipos de nós presentes no grafo")
async def get_node_types(service: KnowledgeService = Depends(get_knowledge_service)):
    types = await service.get_node_types()
    return NodeTypesResponse(types=types)


@router.get("/health", response_model=KnowledgeHealthResponse, summary="Health check da memória semântica")
async def knowledge_health(service: KnowledgeService = Depends(get_knowledge_service)):
    health = await service.get_health_status()
    return KnowledgeHealthResponse(**health)
