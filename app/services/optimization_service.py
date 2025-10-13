import structlog
from typing import Dict, Any, List, Optional

from app.repositories.optimization_repository import (
    optimization_repository,
    OptimizationRepositoryError,
    SystemMetrics,
    DetectedIssue
)

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class OptimizationServiceError(Exception):
    """Base exception for optimization service errors."""
    pass


# --- Optimization Service ---

class OptimizationService:
    """
    Camada de serviço para o ciclo de auto-otimização proativa.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    async def run_optimization_cycle(self, enable_auto_execution: bool, max_improvements: Optional[int]) -> Dict[
        str, Any]:
        logger.info("Orquestrando ciclo de auto-otimização via serviço", auto_execute=enable_auto_execution)
        try:
            # TODO: A lógica de passar os parâmetros para o ciclo deve ser implementada no repositório/core
            return await optimization_repository.run_cycle()
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório de otimização ao executar ciclo", exc_info=e)
            raise OptimizationServiceError("Falha ao executar o ciclo de otimização.") from e

    async def get_system_health(self) -> Dict[str, Any]:
        logger.info("Orquestrando busca de saúde do sistema via serviço.")
        try:
            metrics = await optimization_repository.get_metrics()
            health_score = optimization_repository.get_health_score(metrics)
            return {
                "health_score": health_score,
                "avg_response_time": metrics.avg_response_time,
                "error_rate": metrics.error_rate,
                "tool_success_rate": metrics.tool_success_rate,
                "active_tools_count": metrics.active_tools_count,
                "failed_tools": metrics.failed_tools,
                "slow_tools": metrics.slow_tools
            }
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise OptimizationServiceError("Falha ao buscar as métricas de saúde.") from e

    def get_detected_issues(self, severity: Optional[str], category: Optional[str]) -> List[DetectedIssue]:
        logger.info("Orquestrando busca de problemas detectados via serviço.")
        issues = optimization_repository.find_issues()

        # A lógica de negócio (filtragem) permanece no serviço
        filtered_issues = issues
        if severity:
            severity_thresholds = {"HIGH": 0.7, "MEDIUM": 0.4, "LOW": 0.0}
            threshold = severity_thresholds.get(severity.upper(), 0.0)
            filtered_issues = [i for i in filtered_issues if i.severity >= threshold]
        if category:
            filtered_issues = [i for i in filtered_issues if category.upper() in i.issue_type.value.upper()]

        return filtered_issues

    async def get_metrics_history(self, limit: int) -> List[SystemMetrics]:
        logger.info("Buscando histórico de métricas via serviço.")
        limit = min(limit, 100)
        history = optimization_repository.get_metrics_history()
        return history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        logger.info("Buscando status do módulo de otimização via serviço.")
        return optimization_repository.get_status()


# Instância única do serviço
optimization_service = OptimizationService()
