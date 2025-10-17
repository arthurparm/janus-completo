import structlog
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.services.llm_service import (
    LLMService,
    get_llm_service,
    LLMServiceError
)
from app.core.llm import ModelRole, ModelPriority
from app.core.monitoring.health_monitor import check_llm_manager_health

router = APIRouter(tags=["LLM"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class LLMInvokeRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    role: str = Field("orchestrator")
    priority: str = Field("fast_and_cheap")
    timeout_seconds: Optional[int] = None
    user_id: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)

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
async def invoke_llm(
        request: LLMInvokeRequest,
        service: LLMService = Depends(get_llm_service)
):
    """Delega a invocação de um LLM para o LLMService."""
    # ValueError, LLMTimeoutError, e LLMInvocationError são tratados pelo exception handler central.
    role = ModelRole(request.role)
    priority = ModelPriority(request.priority)

    result = service.invoke_llm(
        prompt=request.prompt,
        role=role,
        priority=priority,
        timeout_seconds=request.timeout_seconds,
        user_id=request.user_id,
        project_id=request.project_id
    )
    return LLMInvokeResponse(**result)

@router.get("/cache/status", response_model=LLMCacheStatusResponse, summary="Retorna o status do cache de LLMs")
async def get_cache_status(service: LLMService = Depends(get_llm_service)):
    """Delega a busca do status do cache para o LLMService."""
    entries = service.get_cache_status()
    return LLMCacheStatusResponse(total_cached=len(entries), cache_entries=entries)

@router.post("/cache/invalidate", summary="Invalida o cache de LLMs")
async def invalidate_llm_cache(
        provider: Optional[str] = None,
        service: LLMService = Depends(get_llm_service)
):
    """Delega a invalidação do cache para o LLMService."""
    remaining_count = service.invalidate_cache(provider)
    message = f"Cache invalidado para provider: {provider}" if provider else "Cache completamente invalidado"
    return {"message": message, "provider": provider, "remaining_cached": remaining_count}


@router.get("/circuit-breakers", response_model=List[CircuitBreakerStatus],
            summary="Retorna o status dos circuit breakers")
async def get_circuit_breaker_status(service: LLMService = Depends(get_llm_service)):
    """Delega a busca do status dos circuit breakers para o LLMService."""
    return service.get_circuit_breaker_statuses()

@router.post("/circuit-breakers/{provider}/reset", summary="Reseta o circuit breaker de um provedor")
async def reset_circuit_breaker(
        provider: str,
        service: LLMService = Depends(get_llm_service)
):
    """Delega o reset do circuit breaker para o LLMService."""
    # LLMServiceError (para provider não encontrado) é tratado pelo handler central.
    new_state = service.reset_circuit_breaker(provider)
    return {"message": f"Circuit breaker resetado para: {provider}", "new_state": new_state}


@router.get("/providers", summary="Lista provedores configurados de LLMs")
async def list_llm_providers(service: LLMService = Depends(get_llm_service)):
    """Retorna os provedores configurados com seus modelos e estado de habilitação."""
    return service.get_providers()


@router.get("/health", summary="Health check do sistema de LLMs")
async def llm_health(service: LLMService = Depends(get_llm_service)):
    """Delega a verificação de saúde para o LLMService."""
    return await service.get_health_status()
