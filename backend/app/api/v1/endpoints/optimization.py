from dataclasses import asdict
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.optimization.self_optimization import IssueSeverity, IssueType
from app.core.security.actor_context import ActorContext
from app.core.security.request_guard import require_service_actor_context
from app.services.optimization_service import (
    OptimizationAnalysisType,
    OptimizationContinuousAlreadyRunningError,
    OptimizationContinuousNotRunningError,
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
    audit_recorded: Literal[True]


class SystemHealthResponse(BaseModel):
    health_score: float
    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    active_tools_count: int
    failed_tools: list[str]
    slow_tools: list[str]


class SystemMetricsResponse(BaseModel):
    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    memory_usage_mb: float | None
    active_tools_count: int
    failed_tools: list[str]
    slow_tools: list[str]
    timestamp: float


class MetricsHistoryResponse(BaseModel):
    count: int = Field(ge=0)
    metrics: list[SystemMetricsResponse]


class ContinuousOptimizationStartRequest(BaseModel):
    interval_seconds: float = Field(300, ge=10, le=86400)


class OptimizationStatusResponse(BaseModel):
    status: Literal["idle", "starting", "running"]
    module: Literal["self_optimization"]
    continuous_running: bool
    continuous_task_active: bool
    continuous_control_available: bool
    automatic_execution_available: bool
    interval_seconds: float | None
    last_started_by: str | None
    last_started_at: float | None
    last_stopped_at: float | None
    last_error: str | None
    last_cycle_at: float | None
    last_issues_detected: int | None
    last_improvements_planned: int | None


class ContinuousOptimizationStartResponse(OptimizationStatusResponse):
    audit_recorded: bool


class ContinuousOptimizationStopResponse(OptimizationStatusResponse):
    stopped: bool
    forced: bool
    audit_recorded: bool


class DetectedIssueResponse(BaseModel):
    issue_type: str
    severity: float
    description: str
    affected_component: str
    detected_at: float


class SystemAnalysisResponse(BaseModel):
    analysis_type: OptimizationAnalysisType
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
    actor: ActorContext = Depends(require_service_actor_context),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationCycleResponse:
    """Delega a execução do ciclo de auto-otimização para o OptimizationService."""
    # OptimizationServiceError é tratado pelo exception handler central -> 500
    try:
        result = await service.run_optimization_cycle(
            enable_auto_execution=request.enable_auto_execution,
            max_improvements=request.max_improvements,
            actor=actor,
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
    severity: IssueSeverity | None = Query(default=None),
    category: IssueType | None = Query(default=None),
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


@router.get(
    "/metrics/history",
    response_model=MetricsHistoryResponse,
    summary="Retorna o histórico de métricas de saúde",
)
async def get_metrics_history(
    limit: int = Query(20, ge=1, le=100),
    service: OptimizationService = Depends(get_optimization_service),
) -> MetricsHistoryResponse:
    """Delega a busca do histórico de métricas para o OptimizationService."""
    history = await service.get_metrics_history(limit)
    return MetricsHistoryResponse(
        count=len(history),
        metrics=[SystemMetricsResponse(**asdict(item)) for item in history],
    )


@router.post(
    "/continuous/start",
    response_model=ContinuousOptimizationStartResponse,
    summary="Inicia o planejamento contínuo de otimizações",
)
async def start_continuous_optimization(
    request: ContinuousOptimizationStartRequest,
    actor: ActorContext = Depends(require_service_actor_context),
    service: OptimizationService = Depends(get_optimization_service),
) -> ContinuousOptimizationStartResponse:
    try:
        result = await service.start_continuous(
            interval_seconds=request.interval_seconds,
            actor=actor,
        )
    except OptimizationContinuousAlreadyRunningError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ContinuousOptimizationStartResponse(**result)


@router.post(
    "/continuous/stop",
    response_model=ContinuousOptimizationStopResponse,
    summary="Interrompe o planejamento contínuo de otimizações",
)
async def stop_continuous_optimization(
    actor: ActorContext = Depends(require_service_actor_context),
    service: OptimizationService = Depends(get_optimization_service),
) -> ContinuousOptimizationStopResponse:
    try:
        result = await service.stop_continuous(actor=actor)
    except OptimizationContinuousNotRunningError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ContinuousOptimizationStopResponse(**result)


@router.get(
    "/status",
    response_model=OptimizationStatusResponse,
    summary="Status do módulo de auto-otimização",
)
async def get_optimization_status(
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationStatusResponse:
    """Delega a busca de status do módulo para o OptimizationService."""
    return OptimizationStatusResponse(**service.get_status())


@router.post(
    "/analyze",
    response_model=SystemAnalysisResponse,
    summary="Analisa métricas e problemas do sistema",
)
async def analyze_system(
    analysis_type: OptimizationAnalysisType = OptimizationAnalysisType.PERFORMANCE,
    detailed: bool = True,
    service: OptimizationService = Depends(get_optimization_service),
) -> SystemAnalysisResponse:
    """Delega a análise agregada do sistema para o OptimizationService."""
    result = await service.analyze_system(analysis_type=analysis_type, detailed=detailed)
    return SystemAnalysisResponse(**result)
