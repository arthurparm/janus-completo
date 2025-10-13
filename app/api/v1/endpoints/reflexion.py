import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.reflexion_service import (
    reflexion_service,
    ReflexionServiceError,
    ReflexionValidationError,
    ReflexionTimeoutError
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
async def execute_with_reflexion(request: ReflexionRequest):
    """Delega a execução de uma tarefa com o ciclo de auto-otimização para o ReflexionService."""
    try:
        config_overrides = {
            "max_iterations": request.max_iterations,
            "max_time_seconds": request.max_time_seconds,
            "success_threshold": request.success_threshold,
        }
        result = await reflexion_service.run_reflexion_cycle(request.task, config_overrides)

        # O serviço já retorna um dict serializável, então podemos passar diretamente
        return ReflexionResponse(**result)

    except ReflexionValidationError as e:
        logger.warning("Erro de validação no serviço de Reflexion", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ReflexionTimeoutError as e:
        logger.error("Timeout no serviço de Reflexion", error=str(e))
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except ReflexionServiceError as e:
        logger.error("Erro no serviço de Reflexion", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/config", summary="Obtém configuração padrão do Reflexion")
async def get_reflexion_config():
    """Retorna a configuração padrão do sistema Reflexion, via serviço."""
    config = reflexion_service.get_config()
    return {
        "max_iterations": config.max_iterations,
        "max_time_seconds": config.max_time_seconds,
        "success_threshold": config.success_threshold
    }


@router.post("/reset-circuit-breaker", summary="Reseta o circuit breaker dos agentes")
async def reset_circuit_breaker():
    """Delega o reset dos circuit breakers para o ReflexionService."""
    try:
        reflexion_service.reset_agent_breakers()
        return {"status": "success", "message": "Circuit breakers dos agentes resetados."}
    except Exception as e:
        logger.error("Erro ao resetar circuit breakers via serviço", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Falha ao resetar circuit breakers.")


@router.get("/health", summary="Verifica saúde do módulo Reflexion")
async def reflexion_health():
    """Delega a verificação de saúde do módulo para o ReflexionService."""
    try:
        health_status = reflexion_service.get_health_status()
        health_status["sprint"] = 5  # Adiciona o número do sprint para compatibilidade
        return health_status
    except Exception as e:
        logger.error("Falha no health check do serviço de Reflexion", exc_info=e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
