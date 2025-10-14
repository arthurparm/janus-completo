from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel
import structlog

from app.services.knowledge_service import KnowledgeService, get_knowledge_service

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])
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

# --- Endpoints ---

@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código")
async def trigger_indexing(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.index_codebase()

@router.post("/consolidate", response_model=IndexResponse, summary="Inicia a consolidação de experiências")
async def trigger_consolidation(service: KnowledgeService = Depends(get_knowledge_service)):
    return await service.trigger_consolidation(limit=10)

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
