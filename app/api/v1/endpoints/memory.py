from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.memory import memory_core
from app.models.schemas import Experience

router = APIRouter()


class MemorizeRequest(BaseModel):
    type: str
    content: str
    metadata: Optional[dict] = {}


class RecallResponse(BaseModel):
    id: str
    content: str
    metadata: dict
    distance: float


@router.post(
    "/memorize",
    response_model=Experience,
    summary="Adiciona uma nova experiência à memória episódica",
    tags=["Memory"]
)
def add_memory(request: MemorizeRequest):
    try:
        experience = Experience(
            type=request.type,
            content=request.content,
            metadata=request.metadata
        )
        memory_core.memorize(experience)
        return experience
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recall",
    response_model=List[RecallResponse],
    summary="Recupera experiências da memória",
    tags=["Memory"]
)
def recall_memories(query: str = Query(..., description="Consulta em linguagem natural para buscar memórias.")):
    try:
        results = memory_core.recall(query=query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
