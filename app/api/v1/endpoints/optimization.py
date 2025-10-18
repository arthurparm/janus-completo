import structlog
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends
from dataclasses import asdict
from pydantic import BaseModel, Field

from app.services.optimization_service import (
    OptimizationService,
    get_optimization_service,
    DetectedIssue
)

router = APIRouter(tags=["Optimization"])
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


class SystemAnalysisResponse(BaseModel):
    analysis_type: str
    score: float
    issues_count: int
    issues_by_type: dict[str, int]
    metrics_snapshot: dict
    trend: dict
    series: Dict[str, List[float]]
    insights: list[str]
    details: Optional[dict] = None

# --- Endpoints ---

@router.post("/run-cycle", response_model=OptimizationCycleResponse, summary="Executa um ciclo de auto-otimização")
async def run_optimization_cycle(
        request: OptimizationCycleRequest,
        service: OptimizationService = Depends(get_optimization_service)
):
    """Delega a execução do ciclo de auto-otimização para o OptimizationService."""
    # OptimizationServiceError é tratado pelo exception handler central -> 500
    result = await service.run_optimization_cycle(
        enable_auto_execution=request.enable_auto_execution,
        max_improvements=request.max_improvements
    )
    return OptimizationCycleResponse(**result)

@router.get("/health", response_model=SystemHealthResponse, summary="Verifica a saúde geral do sistema")
async def get_system_health(service: OptimizationService = Depends(get_optimization_service)):
    """Delega a coleta de métricas de saúde para o OptimizationService."""
    health_data = await service.get_system_health()
    return SystemHealthResponse(**health_data)

@router.get("/issues", response_model=List[DetectedIssueResponse], summary="Lista problemas detectados no sistema")
async def get_detected_issues(
        service: OptimizationService = Depends(get_optimization_service),
        severity: Optional[str] = None,
        category: Optional[str] = None
):
    """Delega a detecção e filtragem de problemas para o OptimizationService."""
    issues = service.get_detected_issues(severity, category)
    return [DetectedIssueResponse(
        issue_type=issue.issue_type.value,
        severity=issue.severity,
        description=issue.description,
        affected_component=issue.affected_component,
        detected_at=issue.detected_at
    ) for issue in issues]

@router.get("/metrics/history", summary="Retorna o histórico de métricas de saúde")
async def get_metrics_history(
        limit: int = 20,
        service: OptimizationService = Depends(get_optimization_service)
):
    """Delega a busca do histórico de métricas para o OptimizationService."""
    history = await service.get_metrics_history(limit)
    return {"count": len(history), "metrics": [asdict(h) for h in history]}

@router.get("/status", summary="Status do módulo de auto-otimização")
async def get_optimization_status(service: OptimizationService = Depends(get_optimization_service)):
    """Delega a busca de status do módulo para o OptimizationService."""
    return service.get_status()


@router.post("/analyze", response_model=SystemAnalysisResponse, summary="Analisa métricas e problemas do sistema")
async def analyze_system(
        analysis_type: str = "performance",
        detailed: bool = True,
        service: OptimizationService = Depends(get_optimization_service)
):
    """Delega a análise agregada do sistema para o OptimizationService."""
    result = await service.analyze_system(analysis_type=analysis_type, detailed=detailed)
    return SystemAnalysisResponse(**result)
