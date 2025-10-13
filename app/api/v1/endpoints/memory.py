from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
import structlog

from app.services.memory_service import memory_service, MemoryServiceError
from app.models.schemas import Experience

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class MemorizeRequest(BaseModel):
    type: str
    content: str
    metadata: Optional[Dict[str, Any]] = {}

class RecallResponse(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


# --- Endpoint ---

@router.post(
    "/memorize",
    response_model=Experience,
    summary="Adiciona uma nova experiência à memória episódica",
    tags=["Memory"]
)
async def add_memory(request: MemorizeRequest):
    """Recebe e delega a criação de uma nova experiência para o MemoryService."""
    try:
        experience = await memory_service.add_experience(
            type=request.type,
            content=request.content,
            metadata=request.metadata
        )
        return experience
    except MemoryServiceError as e:
        logger.error("Erro no serviço de memória ao adicionar experiência", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.critical("Erro inesperado na API de memorização", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Ocorreu um erro inesperado no servidor.")

@router.get(
    "/recall",
    response_model=List[RecallResponse],
    summary="Recupera experiências da memória",
    tags=["Memory"]
)
async def recall_memories(query: str = Query(..., description="Consulta em linguagem natural para buscar memórias.")):
    """Recebe uma consulta e delega a busca para o MemoryService."""
    try:
        return await memory_service.recall_experiences(query=query)
    except MemoryServiceError as e:
        logger.error("Erro no serviço de memória ao buscar experiências", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.critical("Erro inesperado na API de busca de memória", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Ocorreu um erro inesperado no servidor.")
