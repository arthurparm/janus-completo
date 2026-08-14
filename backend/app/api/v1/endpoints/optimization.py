from dataclasses import asdict
from typing import Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.optimization_service import (
    OptimizationExecutionUnavailableError,
    OptimizationService,
    get_optimization_service,
)

router = APIRouter(tags=["Optimization"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class OptimizationCycleRequest(BaseModel):
    enable_auto_execution: bool = Field(False)
    max_improvements: int | None = Field(None, ge=1, le=10)


class PlannedImprovementResponse(BaseModel):
    improvement_type: str
    target_component: str
    description: str
    hypothesis: str
    evidence: dict[str, Any]
    success_criteria: list[str]
    implementation_steps: list[str]
    risk_level: float = Field(ge=0.0, le=1.0)
    priority_score: float
    requires_human_approval: bool


class OptimizationCycleResponse(BaseModel):
    success: bool
    issues_detected: int
    improvements_planned: int
    improvements_applied: int
    elapsed_seconds: float
    plans: list[PlannedImprovementResponse] = Field(default_factory=list)
    message: str


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


class SystemAnalysisResponse(BaseModel):
    analysis_type: str
    score: float
    issues_count: int
    issues_by_type: dict[str, int]
    metrics_snapshot: dict[str, Any]
    trend: dict[str, Any]
    series: dict[str, list[float]]
    insights: list[str]
    details: dict[str, Any] | None = None


# --- Endpoints ---


@router.post(
    "/run-cycle",
    response_model=OptimizationCycleResponse,
    summary="Executa um ciclo de auto-otimização",
    responses={
        status.HTTP_501_NOT_IMPLEMENTED: {
            "description": "A execução automática não possui adaptador auditável."
        }
    },
)
async def run_optimization_cycle(
    request: OptimizationCycleRequest,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationCycleResponse:
    """Delega a execução do ciclo de auto-otimização para o OptimizationService."""
    # OptimizationServiceError é tratado pelo exception handler central -> 500
    try:
        result = await service.run_optimization_cycle(
            enable_auto_execution=request.enable_auto_execution,
            max_improvements=request.max_improvements,
        )
    except OptimizationExecutionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    return OptimizationCycleResponse(**result)


@router.get(
    "/health", response_model=SystemHealthResponse, summary="Verifica a saúde geral do sistema"
)
async def get_system_health(
    service: OptimizationService = Depends(get_optimization_service),
) -> SystemHealthResponse:
    """Delega a coleta de métricas de saúde para o OptimizationService."""
    health_data = await service.get_system_health()
    return SystemHealthResponse(**health_data)


@router.get(
    "/issues",
    response_model=list[DetectedIssueResponse],
    summary="Lista problemas detectados no sistema",
)
async def get_detected_issues(
    service: OptimizationService = Depends(get_optimization_service),
    severity: str | None = None,
    category: str | None = None,
) -> list[DetectedIssueResponse]:
    """Delega a detecção e filtragem de problemas para o OptimizationService."""
    issues = await service.get_detected_issues(severity, category)
    return [
        DetectedIssueResponse(
            issue_type=issue.issue_type.value,
            severity=issue.severity,
            description=issue.description,
            affected_component=issue.affected_component,
            detected_at=issue.detected_at,
        )
        for issue in issues
    ]


@router.get("/metrics/history", summary="Retorna o histórico de métricas de saúde")
async def get_metrics_history(
    limit: int = 20, service: OptimizationService = Depends(get_optimization_service)
) -> dict[str, Any]:
    """Delega a busca do histórico de métricas para o OptimizationService."""
    history = await service.get_metrics_history(limit)
    return {"count": len(history), "metrics": [asdict(h) for h in history]}


@router.get("/status", summary="Status do módulo de auto-otimização")
async def get_optimization_status(
    service: OptimizationService = Depends(get_optimization_service),
) -> dict[str, Any]:
    """Delega a busca de status do módulo para o OptimizationService."""
    return cast(dict[str, Any], service.get_status())


@router.post(
    "/analyze",
    response_model=SystemAnalysisResponse,
    summary="Analisa métricas e problemas do sistema",
)
async def analyze_system(
    analysis_type: str = "performance",
    detailed: bool = True,
    service: OptimizationService = Depends(get_optimization_service),
) -> SystemAnalysisResponse:
    """Delega a análise agregada do sistema para o OptimizationService."""
    result = await service.analyze_system(analysis_type=analysis_type, detailed=detailed)
    return SystemAnalysisResponse(**result)
