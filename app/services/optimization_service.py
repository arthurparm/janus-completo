import structlog
from typing import Dict, Any, List, Optional
from fastapi import Request

from app.repositories.optimization_repository import (
    OptimizationRepository,
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
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: OptimizationRepository):
        self._repo = repo

    async def run_optimization_cycle(self, enable_auto_execution: bool, max_improvements: Optional[int]) -> Dict[
        str, Any]:
        logger.info("Orquestrando ciclo de auto-otimização via serviço", auto_execute=enable_auto_execution)
        try:
            return await self._repo.run_cycle(
                enable_auto_execution=enable_auto_execution,
                max_improvements=max_improvements
            )
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório de otimização ao executar ciclo", exc_info=e)
            raise OptimizationServiceError("Falha ao executar o ciclo de otimização.") from e

    async def get_system_health(self) -> Dict[str, Any]:
        logger.info("Orquestrando busca de saúde do sistema via serviço.")
        try:
            metrics = await self._repo.get_metrics()
            health_score = self._repo.get_health_score(metrics)
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
        issues = self._repo.find_issues()
        
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
        history = self._repo.get_metrics_history()
        return history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        logger.info("Buscando status do módulo de otimização via serviço.")
        return self._repo.get_status()

    async def analyze_system(self, analysis_type: str, detailed: bool) -> Dict[str, Any]:
        """Gera análise agregada do sistema a partir de métricas e issues."""
        logger.info(
            "Orquestrando análise do sistema via serviço.",
            analysis_type=analysis_type,
            detailed=detailed
        )
        try:
            metrics = await self._repo.get_metrics()
            history = self._repo.get_metrics_history()
            issues = self._repo.find_issues()

            # Coletar séries de valores
            resp_times = [m.avg_response_time for m in history] or [metrics.avg_response_time]
            error_rates = [m.error_rate for m in history] or [metrics.error_rate]
            memory_usage = [m.memory_usage_mb for m in history] or [metrics.memory_usage_mb]

            def percentile(values: List[float], p: int) -> float:
                if not values:
                    return 0.0
                s = sorted(values)
                idx = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
                return s[idx]

            trend = {
                "avg_response_time_p95": round(percentile(resp_times, 95), 3),
                "avg_response_time_latest": round(resp_times[-1], 3),
                "error_rate_avg": round(sum(error_rates) / len(error_rates), 3) if error_rates else 0.0,
                "memory_usage_latest_mb": round(memory_usage[-1], 2),
                "memory_usage_max_mb": round(max(memory_usage), 2) if memory_usage else 0.0,
            }

            issues_by_type: Dict[str, int] = {}
            for issue in issues:
                key = issue.issue_type.value
                issues_by_type[key] = issues_by_type.get(key, 0) + 1

            insights: List[str] = []
            if trend["avg_response_time_p95"] > 2.0:
                insights.append("Latência p95 elevada (>2s). Considere otimizações de desempenho.")
            if trend["error_rate_avg"] > 0.2:
                insights.append("Taxa média de erro alta (>20%). Investigue falhas recorrentes.")
            if len(memory_usage) > 10 and trend["memory_usage_latest_mb"] >= trend["memory_usage_max_mb"] * 0.95:
                insights.append("Uso de memória em alta persistente. Possível vazamento de memória.")

            analysis: Dict[str, Any] = {
                "analysis_type": analysis_type,
                "score": self._repo.get_health_score(metrics),
                "issues_count": len(issues),
                "issues_by_type": issues_by_type,
                "metrics_snapshot": {
                    "avg_response_time": metrics.avg_response_time,
                    "error_rate": metrics.error_rate,
                    "tool_success_rate": metrics.tool_success_rate,
                    "active_tools_count": metrics.active_tools_count,
                    "failed_tools": metrics.failed_tools,
                    "slow_tools": metrics.slow_tools,
                    "memory_usage_mb": metrics.memory_usage_mb,
                },
                "trend": trend,
                "insights": insights,
            }

            if detailed:
                analysis["details"] = {
                    "history_count": len(history),
                    "issues": [
                        {
                            "type": i.issue_type.value,
                            "severity": i.severity,
                            "component": i.affected_component,
                            "description": i.description,
                            "detected_at": i.detected_at,
                            "evidence": i.evidence,
                        }
                        for i in issues
                    ],
                }

            return analysis

        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório ao analisar sistema", exc_info=e)
            raise OptimizationServiceError("Falha ao analisar o sistema.") from e

# Padrão de Injeção de Dependência: Getter para o serviço
def get_optimization_service(request: Request) -> OptimizationService:
    return request.app.state.optimization_service
