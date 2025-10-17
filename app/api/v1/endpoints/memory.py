from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
import structlog
from datetime import datetime

from app.services.memory_service import MemoryService, get_memory_service
from app.models.schemas import Experience

router = APIRouter(tags=["Memory"])
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
        limit: Optional[int] = Query(None, ge=1, le=50, description="Máximo de resultados a retornar."),
        min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Pontuação mínima (0..1) para filtrar resultados."),
        service: MemoryService = Depends(get_memory_service)
):
    """
    Delega a busca por experiências para o MemoryService.
    O tratamento de erros é feito pelo exception handler central.
    """
    return await service.recall_experiences(query=query, limit=limit, min_score=min_score)

# --- Advanced recall endpoints ---

@router.get(
    "/recall/filtered",
    response_model=List[RecallResponse],
    summary="Busca memórias com filtros por payload"
)
async def recall_filtered(
        query: Optional[str] = Query(None, description="Consulta em linguagem natural (opcional)."),
        type: Optional[str] = Query(None, description="Filtrar por tipo da experiência."),
        origin: Optional[str] = Query(None, description="Filtrar por metadata.origin"),
        status: Optional[str] = Query(None, description="Filtrar por metadata.status"),
        limit: Optional[int] = Query(None, ge=1, le=50, description="Máximo de resultados a retornar."),
        min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Pontuação mínima (0..1) para filtrar resultados."),
        service: MemoryService = Depends(get_memory_service)
):
    filters: Dict[str, Any] = {}
    if type is not None:
        filters["type"] = type
    if origin is not None:
        filters["origin"] = origin
    if status is not None:
        filters["status"] = status
    return await service.recall_filtered(query=query, filters=filters, limit=limit, min_score=min_score)


def _to_ts_ms(iso_str: Optional[str]) -> Optional[int]:
    if iso_str is None:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

@router.get(
    "/recall/timeframe",
    response_model=List[RecallResponse],
    summary="Busca memórias por janela temporal"
)
async def recall_by_timeframe(
        query: Optional[str] = Query(None, description="Consulta em linguagem natural (opcional)."),
        start: Optional[str] = Query(None, description="Início ISO-8601 (ex.: 2025-01-01T00:00:00+00:00)"),
        end: Optional[str] = Query(None, description="Fim ISO-8601 (ex.: 2025-01-02T00:00:00+00:00)"),
        limit: Optional[int] = Query(None, ge=1, le=50),
        min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Pontuação mínima (0..1) para filtrar resultados."),
        service: MemoryService = Depends(get_memory_service)
):
    start_ms = _to_ts_ms(start)
    end_ms = _to_ts_ms(end)
    return await service.recall_by_timeframe(query=query, start_ts_ms=start_ms, end_ts_ms=end_ms, limit=limit, min_score=min_score)

@router.get(
    "/recall/recent_failures",
    response_model=List[RecallResponse],
    summary="Lista falhas recentes na janela (por padrão, janela de cota do sistema)"
)
async def recall_recent_failures(
        timeframe_seconds: Optional[int] = Query(None, ge=60, le=86400, description="Janela em segundos (padrão: configuração do sistema)."),
        limit: Optional[int] = Query(None, ge=1, le=50),
        min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Pontuação mínima (0..1) para filtrar resultados."),
        service: MemoryService = Depends(get_memory_service)
):
    return await service.recall_recent_failures(limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
