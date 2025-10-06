"""
Sprint 7: Endpoint de Auto-Otimização Proativa

API REST para monitorar e controlar o sistema de auto-otimização do Janus.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.problem_details import ProblemDetails
from app.core.optimization import self_optimization_cycle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization", tags=["optimization"])


# ==================== SCHEMAS ====================

class OptimizationCycleResponse(BaseModel):
    """Resposta de um ciclo de otimização."""
    success: bool
    issues_detected: Optional[int] = None
    improvements_planned: Optional[int] = None
    improvements_applied: Optional[int] = None
    elapsed_seconds: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """Resposta de saúde do sistema."""
    health_score: float = Field(..., description="Score de saúde (0.0-1.0)")
    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    active_tools_count: int
    failed_tools: list[str]
    slow_tools: list[str]


class DetectedIssueResponse(BaseModel):
    """Problema detectado."""
    issue_type: str
    severity: float
    description: str
    affected_component: str
    detected_at: float


# ==================== ENDPOINTS ====================

@router.post(
    "/run-cycle",
    response_model=OptimizationCycleResponse,
    summary="Executa ciclo de auto-otimização",
    description=(
            "Executa manualmente um ciclo completo de auto-otimização: "
            "monitora sistema, detecta problemas, planeja melhorias e as aplica autonomamente."
    )
)
async def run_optimization_cycle():
    """
    Executa ciclo completo de auto-otimização.

    O sistema irá:
    1. Coletar métricas de performance
    2. Detectar problemas e gargalos
    3. Planejar melhorias específicas
    4. Executar melhorias de forma autônoma
    5. Aprender com os resultados

    Exemplo de resposta:
    ```json
    {
        "success": true,
        "issues_detected": 3,
        "improvements_planned": 2,
        "improvements_applied": 2,
        "elapsed_seconds": 45.3
    }
    ```
    """
    try:
        logger.info("[Optimization API] Executando ciclo de auto-otimização")

        result = await self_optimization_cycle.run_cycle()

        return OptimizationCycleResponse(**result)

    except Exception as e:
        logger.error(f"[Optimization API] Erro ao executar ciclo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ProblemDetails(
                type="optimization_error",
                title="Erro no Ciclo de Otimização",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
                instance="/api/v1/optimization/run-cycle"
            ).model_dump()
        )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Verifica saúde do sistema",
    description="Retorna métricas agregadas sobre a saúde e performance do sistema"
)
async def get_system_health():
    """
    Obtém métricas de saúde do sistema.

    Retorna:
    - Score de saúde geral (0.0-1.0)
    - Tempo médio de resposta
    - Taxa de erro
    - Taxa de sucesso de ferramentas
    - Lista de ferramentas com problemas

    Exemplo:
    ```json
    {
        "health_score": 0.85,
        "avg_response_time": 0.45,
        "error_rate": 0.05,
        "tool_success_rate": 0.95,
        "active_tools_count": 15,
        "failed_tools": ["faulty_calculator"],
        "slow_tools": ["slow_database_query"]
    }
    ```
    """
    try:
        # Coleta métricas atuais
        metrics = await self_optimization_cycle.monitor.collect_metrics()

        health_score = self_optimization_cycle.monitor._calculate_health_score(metrics)

        return SystemHealthResponse(
            health_score=health_score,
            avg_response_time=metrics.avg_response_time,
            error_rate=metrics.error_rate,
            tool_success_rate=metrics.tool_success_rate,
            active_tools_count=metrics.active_tools_count,
            failed_tools=metrics.failed_tools,
            slow_tools=metrics.slow_tools
        )

    except Exception as e:
        logger.error(f"[Optimization API] Erro ao obter saúde do sistema: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/issues",
    response_model=list[DetectedIssueResponse],
    summary="Lista problemas detectados",
    description="Retorna lista de problemas detectados no sistema que requerem atenção"
)
async def get_detected_issues():
    """
    Lista problemas detectados no sistema.

    Analisa métricas recentes e identifica:
    - Taxa de erro elevada
    - Ferramentas falhando
    - Ferramentas lentas
    - Degradação de performance
    - Memory leaks
    - Esgotamento de recursos

    Exemplo:
    ```json
    [
        {
            "issue_type": "tool_failure",
            "severity": 0.7,
            "description": "Ferramenta 'faulty_calculator' com alta taxa de falha",
            "affected_component": "faulty_calculator",
            "detected_at": 1704826800.0
        }
    ]
    ```
    """
    try:
        issues = self_optimization_cycle.monitor.detect_issues()

        return [
            DetectedIssueResponse(
                issue_type=issue.issue_type.value,
                severity=issue.severity,
                description=issue.description,
                affected_component=issue.affected_component,
                detected_at=issue.detected_at
            )
            for issue in issues
        ]

    except Exception as e:
        logger.error(f"[Optimization API] Erro ao detectar problemas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/metrics/history",
    summary="Histórico de métricas",
    description="Retorna histórico recente de métricas do sistema"
)
async def get_metrics_history(limit: int = 20):
    """
    Obtém histórico de métricas do sistema.

    Query params:
    - limit: Número de registros a retornar (padrão: 20, máx: 100)

    Retorna série temporal de métricas coletadas.
    """
    try:
        limit = min(limit, 100)  # Máximo 100 registros

        history = self_optimization_cycle.monitor._metrics_history[-limit:]

        return {
            "count": len(history),
            "metrics": [
                {
                    "timestamp": m.timestamp,
                    "avg_response_time": m.avg_response_time,
                    "error_rate": m.error_rate,
                    "tool_success_rate": m.tool_success_rate,
                    "active_tools_count": m.active_tools_count,
                    "failed_tools": m.failed_tools,
                    "slow_tools": m.slow_tools
                }
                for m in history
            ]
        }

    except Exception as e:
        logger.error(f"[Optimization API] Erro ao obter histórico: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/status",
    summary="Status do módulo de auto-otimização",
    description="Retorna status atual do sistema de auto-otimização"
)
async def get_optimization_status():
    """Health check e status do módulo de auto-otimização."""
    try:
        from app.core.optimization import SystemMonitor

        return {
            "status": "healthy",
            "module": "self_optimization",
            "continuous_running": self_optimization_cycle._running,
            "sprint": 7
        }

    except Exception as e:
        logger.error(f"[Optimization API] Health check falhou: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )
