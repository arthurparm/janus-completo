from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.models.knowledge import CodeEntity
from app.services.knowledge_service import KnowledgeService, get_knowledge_service

router = APIRouter(tags=["Knowledge"])


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
    results: List[RelatedConceptItem]


class EntityRelationshipsItem(BaseModel):
    related_entity: str
    related_type: str
    relationship: str
    distance: int


class EntityRelationshipsResponse(BaseModel):
    results: List[EntityRelationshipsItem]


class ClearGraphResponse(BaseModel):
    status: str
    message: str
    remaining_nodes: int


# --- Sprint 8 DTOs ---

class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10  # Usado pelo pipeline Graph RAG para limitar contexto


class KnowledgeHealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    total_nodes: int
    total_relationships: int


class ConsolidationRequest(BaseModel):
    mode: str = "batch"  # "batch" ou "single"
    limit: int = 10
    min_score: float = 0.0
    experience_id: Optional[str] = None
    experience_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConsolidationResponse(BaseModel):
    message: str
    stats: Dict[str, Any]

# --- Endpoints ---

@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código")
async def trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.index_codebase()


@router.get("/stats", summary="Estatísticas do grafo")
async def get_knowledge_stats(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.get_stats()

@router.get("/entities", response_model=List[CodeEntity], summary="Lista entidades de código")
async def get_code_entities(
        file_path: Optional[str] = Query(None, description="Filtra por caminho de arquivo."),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    return await service.get_code_entities(file_path)


@router.get("/entity/{entity_name}/relationships", response_model=EntityRelationshipsResponse, summary="Navega relacionamentos de uma entidade")
async def get_entity_relationships(
        entity_name: str,
        rel_type: Optional[str] = Query(None, description="Filtra pelo tipo de relacionamento"),
        direction: str = Query("both", regex=r"^(out|in|both)$", description="Direção do relacionamento (out/in/both)"),
        max_depth: int = Query(1, ge=1, le=5, description="Profundidade máxima de navegação"),
        limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
        skip: int = Query(0, ge=0, description="Offset para paginação"),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    rows = await service.get_entity_relationships(entity_name=entity_name, rel_type=rel_type, direction=direction, max_depth=max_depth, limit=limit, skip=skip)
    items = [EntityRelationshipsItem(**row) for row in rows]
    return EntityRelationshipsResponse(results=items)

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
    answer = await service.semantic_query(request.query, limit=request.limit)
    return KnowledgeQueryResponse(answer=answer)


@router.post("/concepts/related", response_model=RelatedConceptsResponse, summary="Busca conceitos relacionados")
async def related_concepts(request: RelatedConceptsRequest, service: KnowledgeService = Depends(get_knowledge_service)):
    results = await service.find_related_concepts(concept=request.concept, max_depth=request.max_depth, limit=request.limit, skip=request.skip)
    items = [RelatedConceptItem(**row) for row in results]
    return RelatedConceptsResponse(results=items)


class NodeTypesResponse(BaseModel):
    types: List[str]

@router.get("/node-types", response_model=NodeTypesResponse, summary="Lista tipos de nós presentes no grafo")
async def get_node_types(service: KnowledgeService = Depends(get_knowledge_service)):
    types = await service.get_node_types()
    return NodeTypesResponse(types=types)


@router.get("/health", response_model=KnowledgeHealthResponse, summary="Health check da memória semântica")
async def knowledge_health(service: KnowledgeService = Depends(get_knowledge_service)):
    health = await service.get_health_status()
    return KnowledgeHealthResponse(**health)


@router.post("/consolidate", response_model=ConsolidationResponse,
             summary="Dispara consolidação de conhecimento via fila")
async def publish_consolidation(request: ConsolidationRequest):
    # Publica tarefa para o worker de consolidação consumir
    from app.core.workers.async_consolidation_worker import publish_consolidation_task
    payload = request.model_dump()
    result = await publish_consolidation_task(payload)
    return ConsolidationResponse(message="Tarefa de consolidação publicada.", stats=result)


@router.get("/functions/calling", response_model=List[CodeEntity],
            summary="Lista funções que chamam a função informada")
async def functions_calling(
        name: str = Query(..., description="Nome da função alvo"),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    rows = await service.get_functions_calling(function_name=name)
    return [CodeEntity(**row) for row in rows]


@router.get("/files/importing", response_model=List[CodeEntity],
            summary="Lista arquivos que importam o módulo/arquivo informado")
async def files_importing(
        module: str = Query(..., description="Nome do módulo ou caminho do arquivo"),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    rows = await service.get_files_importing(module=module)
    return [CodeEntity(**row) for row in rows]


@router.get("/classes/implementations", response_model=List[CodeEntity],
            summary="Lista classes que implementam o protocolo/interface informado")
async def classes_implementations(
        protocol: str = Query(..., description="Nome do protocolo/interface"),
        service: KnowledgeService = Depends(get_knowledge_service)
):
    rows = await service.get_classes_implementing(protocol=protocol)
    return [CodeEntity(**row) for row in rows]
