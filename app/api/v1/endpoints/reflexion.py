import structlog
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.reflexion_service import (
    ReflexionService,
    get_reflexion_service
)

router = APIRouter(prefix="/reflexion", tags=["Reflexion"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class ReflexionRequest(BaseModel):
    task: str = Field(..., min_length=1)
    max_iterations: Optional[int] = Field(None, ge=1, le=10)
    max_time_seconds: Optional[int] = Field(None, ge=30, le=600)
    success_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

class ReflexionResponse(BaseModel):
    success: bool
    best_result: str
    best_score: float
    iterations: int
    lessons_learned: list[str]
    elapsed_seconds: float
    steps: list[dict]

# --- Endpoints ---

@router.post("/execute", response_model=ReflexionResponse, summary="Executa tarefa com o ciclo Reflexion")
async def execute_with_reflexion(
        request: ReflexionRequest,
        service: ReflexionService = Depends(get_reflexion_service)
):
    """
    Delega a execução de uma tarefa com o ciclo de auto-otimização para o ReflexionService.
    O tratamento de erros (Validação, Timeout, etc.) é feito pelo exception handler central.
    """
    config_overrides = {
        "max_iterations": request.max_iterations,
        "max_time_seconds": request.max_time_seconds,
        "success_threshold": request.success_threshold,
    }
    result = await service.run_reflexion_cycle(request.task, config_overrides)
    return ReflexionResponse(**result)

@router.get("/config", summary="Obtém configuração padrão do Reflexion")
async def get_reflexion_config(service: ReflexionService = Depends(get_reflexion_service)):
    """Retorna a configuração padrão do sistema Reflexion, via serviço."""
    config = service.get_config()
    return {
        "max_iterations": config.max_iterations,
        "max_time_seconds": config.max_time_seconds,
        "success_threshold": config.success_threshold
    }

@router.post("/reset-circuit-breaker", summary="Reseta o circuit breaker dos agentes")
async def reset_circuit_breaker(service: ReflexionService = Depends(get_reflexion_service)):
    """Delega o reset dos circuit breakers para o ReflexionService."""
    service.reset_agent_breakers()
    return {"status": "success", "message": "Circuit breakers dos agentes resetados."}

@router.get("/health", summary="Verifica saúde do módulo Reflexion")
async def reflexion_health(service: ReflexionService = Depends(get_reflexion_service)):
    """Delega a verificação de saúde do módulo para o ReflexionService."""
    try:
        health_status = service.get_health_status()
        health_status["sprint"] = 5
        return health_status
    except Exception as e:
        # O handler genérico pode não ser suficiente se quisermos um status 503 específico aqui
        logger.error("Falha no health check do serviço de Reflexion", exc_info=e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
