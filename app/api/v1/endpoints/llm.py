import structlog
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.llm_service import (
    llm_service,
    LLMServiceError,
    LLMInvocationError,
    LLMTimeoutError
)
from app.core.llm import ModelRole, ModelPriority

router = APIRouter(prefix="/llm", tags=["LLM"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class LLMInvokeRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    role: str = Field("orchestrator")
    priority: str = Field("fast_and_cheap")
    timeout_seconds: Optional[int] = None

class LLMInvokeResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str

class LLMCacheStatusResponse(BaseModel):
    total_cached: int
    cache_entries: List[Dict[str, Any]]

class CircuitBreakerStatus(BaseModel):
    provider: str
    state: str
    failure_count: int
    last_failure_time: Optional[float]

# --- Endpoints ---

@router.post("/invoke", response_model=LLMInvokeResponse, summary="Invoca um LLM com base no papel e prioridade")
async def invoke_llm(request: LLMInvokeRequest):
    """Delega a invocação de um LLM para o LLMService."""
    try:
        role = ModelRole(request.role)
        priority = ModelPriority(request.priority)

        result = llm_service.invoke_llm(
            prompt=request.prompt,
            role=role,
            priority=priority,
            timeout_seconds=request.timeout_seconds
        )
        return LLMInvokeResponse(**result)
    except ValueError as e:  # Erro de conversão de enum
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parâmetro inválido: {e}")
    except LLMTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(e))
    except LLMInvocationError as e:
        logger.error("Erro de invocação no serviço de LLM", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cache/status", response_model=LLMCacheStatusResponse, summary="Retorna o status do cache de LLMs")
async def get_cache_status():
    """Delega a busca do status do cache para o LLMService."""
    entries = llm_service.get_cache_status()
    return LLMCacheStatusResponse(total_cached=len(entries), cache_entries=entries)


@router.post("/cache/invalidate", summary="Invalida o cache de LLMs")
async def invalidate_llm_cache(provider: Optional[str] = None):
    """Delega a invalidação do cache para o LLMService."""
    remaining_count = llm_service.invalidate_cache(provider)
    message = f"Cache invalidado para provider: {provider}" if provider else "Cache completamente invalidado"
    return {"message": message, "provider": provider, "remaining_cached": remaining_count}


@router.get("/circuit-breakers", response_model=List[CircuitBreakerStatus],
            summary="Retorna o status dos circuit breakers")
async def get_circuit_breaker_status():
    """Delega a busca do status dos circuit breakers para o LLMService."""
    return llm_service.get_circuit_breaker_statuses()


@router.post("/circuit-breakers/{provider}/reset", summary="Reseta o circuit breaker de um provedor")
async def reset_circuit_breaker(provider: str):
    """Delega o reset do circuit breaker para o LLMService."""
    try:
        new_state = llm_service.reset_circuit_breaker(provider)
        return {"message": f"Circuit breaker resetado para: {provider}", "new_state": new_state}
    except LLMServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
