import structlog
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.optimization_service import (
    optimization_service,
    OptimizationServiceError
)

router = APIRouter(prefix="/optimization", tags=["Optimization"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class OptimizationCycleRequest(BaseModel):
    enable_auto_execution: bool = Field(False)
    max_improvements: Optional[int] = Field(None, ge=1, le=10)

class OptimizationCycleResponse(BaseModel):
    success: bool
    issues_detected: Optional[int] = None
    improvements_planned: Optional[int] = None
    improvements_applied: Optional[int] = None
    elapsed_seconds: Optional[float] = None
    message: Optional[str] = None

class SystemHealthResponse(BaseModel):
    health_score: float
    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    active_tools_count: int
    failed_tools: list[str]
    slow_tools: list[str]

class DetectedIssueResponse(BaseModel):
    issue_type: str
    severity: float
    description: str
    affected_component: str
    detected_at: float


# --- Endpoints ---

@router.post("/run-cycle", response_model=OptimizationCycleResponse, summary="Executa um ciclo de auto-otimização")
async def run_optimization_cycle(request: OptimizationCycleRequest):
    """Delega a execução do ciclo de auto-otimização para o OptimizationService."""
    try:
        result = await optimization_service.run_optimization_cycle(
            enable_auto_execution=request.enable_auto_execution,
            max_improvements=request.max_improvements
        )
        return OptimizationCycleResponse(**result)
    except OptimizationServiceError as e:
        logger.error("Erro no serviço de otimização ao executar ciclo", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health", response_model=SystemHealthResponse, summary="Verifica a saúde geral do sistema")
async def get_system_health():
    """Delega a coleta de métricas de saúde para o OptimizationService."""
    try:
        health_data = await optimization_service.get_system_health()
        return SystemHealthResponse(**health_data)
    except OptimizationServiceError as e:
        logger.error("Erro no serviço de otimização ao buscar saúde do sistema", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/issues", response_model=List[DetectedIssueResponse], summary="Lista problemas detectados no sistema")
async def get_detected_issues(severity: Optional[str] = None, category: Optional[str] = None):
    """Delega a detecção e filtragem de problemas para o OptimizationService."""
    try:
        issues = optimization_service.get_detected_issues(severity, category)
        return [DetectedIssueResponse(
            issue_type=issue.issue_type.value,
            severity=issue.severity,
            description=issue.description,
            affected_component=issue.affected_component,
            detected_at=issue.detected_at
        ) for issue in issues]
    except OptimizationServiceError as e:
        logger.error("Erro no serviço de otimização ao buscar problemas", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/metrics/history", summary="Retorna o histórico de métricas de saúde")
async def get_metrics_history(limit: int = 20):
    """Delega a busca do histórico de métricas para o OptimizationService."""
    try:
        history = await optimization_service.get_metrics_history(limit)
        return {"count": len(history), "metrics": [h.dict() for h in history]}
    except OptimizationServiceError as e:
        logger.error("Erro no serviço de otimização ao buscar histórico de métricas", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/status", summary="Status do módulo de auto-otimização")
async def get_optimization_status():
    """Delega a busca de status do módulo para o OptimizationService."""
    return optimization_service.get_status()
