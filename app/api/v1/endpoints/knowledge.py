from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog

from app.services.knowledge_service import knowledge_service

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---
class IndexResponse(BaseModel):
    message: str
    summary: str

class CodeEntity(BaseModel):
    type: str
    name: str
    file_path: str

class CallRelationship(BaseModel):
    caller_function: str
    caller_file: str
    callee_function: str

class ConsolidateRequest(BaseModel):
    limit: int = 10


class EntityDetailsResponse(BaseModel):
    entity: Dict[str, Any]
    relationships: List[Dict[str, Any]]


class ClearGraphResponse(BaseModel):
    status: str
    message: str
    remaining_nodes: int


# --- Endpoints ---

@router.post("/index", response_model=IndexResponse, summary="Inicia a indexação da base de código",
             tags=["Knowledge Graph"])
async def trigger_indexing():
    """Dispara o processo de varredura do código-fonte para popular o grafo."""
    try:
        result = await knowledge_service.index_codebase()
        return result
    except Exception as e:
        logger.error("Erro ao disparar a indexação da base de código", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate", response_model=IndexResponse, summary="Inicia a consolidação de experiências",
             tags=["Knowledge Graph"])
async def trigger_consolidation(request: ConsolidateRequest):
    """Dispara o processo de consolidação de experiências da memória para o grafo."""
    try:
        result = await knowledge_service.trigger_consolidation(limit=request.limit)
        return result
    except Exception as e:
        logger.error("Erro ao disparar a consolidação de conhecimento", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Estatísticas do grafo", tags=["Knowledge Graph"])
async def get_knowledge_stats():
    """Retorna estatísticas agregadas sobre os nós e relacionamentos no grafo."""
    try:
        return await knowledge_service.get_stats()
    except Exception as e:
        logger.error("Erro ao buscar estatísticas do grafo", exc_info=e)
        raise HTTPException(status_code=500, detail="Falha ao buscar estatísticas do grafo.")


@router.get("/entities", response_model=List[CodeEntity], summary="Lista entidades de código", tags=["Knowledge Graph"])
async def get_code_entities(file_path: Optional[str] = Query(None, description="Filtra por caminho de arquivo.")):
    """Consulta o grafo por nós de Função ou Classe."""
    try:
        return await knowledge_service.get_code_entities(file_path)
    except Exception as e:
        logger.error("Erro ao buscar entidades de código", exc_info=e, file_path=file_path)
        raise HTTPException(status_code=500, detail="Falha ao buscar entidades de código.")


@router.get("/calls", response_model=List[CallRelationship], summary="Lista chamadas de função",
            tags=["Knowledge Graph"])
async def get_function_calls(function_name: Optional[str] = Query(None, description="Filtra por nome da função.")):
    """Consulta o grafo por relações :CALLS entre Funções."""
    try:
        return await knowledge_service.get_function_calls(function_name)
    except Exception as e:
        logger.error("Erro ao buscar chamadas de função", exc_info=e, function_name=function_name)
        raise HTTPException(status_code=500, detail="Falha ao buscar chamadas de função.")


@router.get("/entity/{entity_name}", response_model=EntityDetailsResponse, summary="Obtém detalhes de uma entidade",
            tags=["Knowledge Graph"])
async def get_entity_details(entity_name: str):
    """Busca os detalhes e relacionamentos de uma entidade específica pelo nome."""
    try:
        details = await knowledge_service.get_entity_details(entity_name)
        if not details:
            raise HTTPException(status_code=404, detail=f"Entidade '{entity_name}' não encontrada.")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao buscar detalhes da entidade", exc_info=e, entity_name=entity_name)
        raise HTTPException(status_code=500, detail="Falha ao buscar detalhes da entidade.")


@router.delete("/clear", response_model=ClearGraphResponse, summary="Limpa todo o grafo",
               tags=["Knowledge Graph - Maintenance"])
async def clear_knowledge_graph():
    """
    **ATENÇÃO**: Remove TODOS os nós e relacionamentos do grafo Neo4j.
    """
    try:
        remaining_nodes = await knowledge_service.clear_graph()
        return {
            "status": "success",
            "message": "Grafo de conhecimento limpo com sucesso",
            "remaining_nodes": remaining_nodes
        }
    except Exception as e:
        logger.error("Erro ao limpar o grafo", exc_info=e)
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})
