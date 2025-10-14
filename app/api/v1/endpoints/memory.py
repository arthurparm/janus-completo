from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
import structlog

from app.services.memory_service import MemoryService, get_memory_service
from app.models.schemas import Experience

router = APIRouter(prefix="/memory", tags=["Memory"])
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
    summary="Adiciona uma nova experiência à memória episódica"
)
async def add_memory(
        request: MemorizeRequest,
        service: MemoryService = Depends(get_memory_service)
):
    """
    Delega a criação de uma nova experiência para o MemoryService.
    O tratamento de erros é feito pelo exception handler central.
    """
    return await service.add_experience(
        type=request.type,
        content=request.content,
        metadata=request.metadata
    )

@router.get(
    "/recall",
    response_model=List[RecallResponse],
    summary="Recupera experiências da memória"
)
async def recall_memories(
        query: str = Query(..., description="Consulta em linguagem natural para buscar memórias."),
        service: MemoryService = Depends(get_memory_service)
):
    """
    Delega a busca por experiências para o MemoryService.
    O tratamento de erros é feito pelo exception handler central.
    """
    return await service.recall_experiences(query=query)
