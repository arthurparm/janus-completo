from typing import Any, cast

import structlog

from app.core.optimization import self_optimization_cycle
from app.core.optimization.self_optimization import (
    DetectedIssue,
    OptimizationMetricsUnavailableError,
    SystemMetrics,
)

logger = structlog.get_logger(__name__)


class OptimizationRepositoryError(Exception):
    """Base exception for optimization repository errors."""

    pass


class OptimizationMetricsUnavailableRepositoryError(OptimizationRepositoryError):
    """A telemetria necessária ainda não possui amostras."""


class OptimizationRepository:
    """
    Camada de Repositório para o ciclo de auto-otimização proativa.
    Abstrai todas as interações diretas com a infraestrutura de otimização.
    """

    async def run_cycle(
        self, enable_auto_execution: bool = False, max_improvements: int | None = None
    ) -> dict[str, Any]:
        """Executa o ciclo de otimização através da infraestrutura core."""
        logger.debug("Executando ciclo de otimização via repositório.")
        try:
            return cast(
                dict[str, Any],
                await self_optimization_cycle.run_cycle(
                    enable_auto_execution=enable_auto_execution,
                    max_improvements=max_improvements,
                ),
            )
        except OptimizationMetricsUnavailableError as e:
            raise OptimizationMetricsUnavailableRepositoryError(str(e)) from e
        except Exception as e:
            logger.error("Erro no repositório ao executar ciclo de otimização", exc_info=e)
            raise OptimizationRepositoryError("Falha ao executar o ciclo de otimização.") from e

    async def run_continuous(self, interval_seconds: float) -> None:
        """Executa o planejador contínuo até uma solicitação explícita de parada."""
        try:
            await self_optimization_cycle.run_continuous(interval_seconds=interval_seconds)
        except Exception as e:
            logger.error("Falha no loop contínuo de otimização", exc_info=e)
            raise OptimizationRepositoryError(
                "Falha no loop contínuo de otimização."
            ) from e

    def stop_continuous(self) -> None:
        """Sinaliza a parada do planejador contínuo em execução."""
        self_optimization_cycle.stop()

    async def get_metrics(self) -> SystemMetrics:
        """Coleta as métricas de saúde atuais do sistema."""
        logger.debug("Coletando métricas no repositório de otimização.")
        try:
            return await self_optimization_cycle.monitor.collect_metrics()
        except OptimizationMetricsUnavailableError as e:
            raise OptimizationMetricsUnavailableRepositoryError(str(e)) from e
        except Exception as e:
            logger.error("Erro ao coletar métricas de otimização", exc_info=e)
            raise OptimizationRepositoryError(
                "Falha ao coletar métricas de otimização."
            ) from e

    def get_health_score(self, metrics: SystemMetrics) -> float:
        """Calcula o score de saúde a partir das métricas."""
        return cast(
            float, self_optimization_cycle.monitor._calculate_health_score(metrics)
        )

    def find_issues(self) -> list[DetectedIssue]:
        """Detecta problemas no sistema a partir das métricas."""
        logger.debug("Detectando problemas no repositório de otimização.")
        try:
            return cast(
                list[DetectedIssue],
                self_optimization_cycle.monitor.detect_issues(),
            )
        except Exception as e:
            logger.error("Erro ao detectar problemas de otimização", exc_info=e)
            raise OptimizationRepositoryError(
                "Falha ao detectar problemas de otimização."
            ) from e

    def get_metrics_history(self) -> list[SystemMetrics]:
        """Retorna o histórico de métricas."""
        return cast(
            list[SystemMetrics], self_optimization_cycle.monitor._metrics_history
        )

    def get_status(self) -> dict[str, Any]:
        """Retorna o status de execução do ciclo contínuo."""
        return {
            "status": "running" if self_optimization_cycle._running else "idle",
            "module": "self_optimization",
            "continuous_running": self_optimization_cycle._running,
        }


# Padrão de Injeção de Dependência: Getter para o repositório
def get_optimization_repository() -> OptimizationRepository:
    return OptimizationRepository()
