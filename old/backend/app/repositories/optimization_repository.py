from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.core.optimization.self_optimization import (
    DetectedIssue,
    OptimizationMetricsUnavailableError,
    SystemMetrics,
    self_optimization_cycle,
)
from app.db import db
from app.models.audit_ledger_models import AuditLedgerEvent

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
            return await self_optimization_cycle.run_cycle(
                enable_auto_execution=enable_auto_execution,
                max_improvements=max_improvements,
            )
        except OptimizationMetricsUnavailableError as e:
            raise OptimizationMetricsUnavailableRepositoryError(str(e)) from e
        except Exception as e:
            logger.error("Erro no repositório ao executar ciclo de otimização", exc_info=e)
            raise OptimizationRepositoryError("Falha ao executar o ciclo de otimização.") from e

    async def run_continuous(
        self,
        interval_seconds: float,
        on_cycle_completed: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Executa o planejador contínuo até uma solicitação explícita de parada."""
        try:
            await self_optimization_cycle.run_continuous(
                interval_seconds=interval_seconds,
                on_cycle_completed=on_cycle_completed,
            )
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
        return self_optimization_cycle.monitor._calculate_health_score(metrics)

    def find_issues(self) -> list[DetectedIssue]:
        """Detecta problemas no sistema a partir das métricas."""
        logger.debug("Detectando problemas no repositório de otimização.")
        try:
            return self_optimization_cycle.monitor.detect_issues()
        except Exception as e:
            logger.error("Erro ao detectar problemas de otimização", exc_info=e)
            raise OptimizationRepositoryError(
                "Falha ao detectar problemas de otimização."
            ) from e

    def get_metrics_history(self) -> list[SystemMetrics]:
        """Retorna o histórico de métricas."""
        return self_optimization_cycle.monitor._metrics_history

    def get_status(self) -> dict[str, Any]:
        """Retorna o status de execução do ciclo contínuo."""
        return {
            "status": "running" if self_optimization_cycle._running else "idle",
            "module": "self_optimization",
            "continuous_running": self_optimization_cycle._running,
        }

    def get_persisted_cycle(self, cycle_id: str) -> dict[str, Any] | None:
        """Recupera um ciclo confirmado pelo ledger imutável."""
        session = db.get_session_direct()
        try:
            query = session.query(AuditLedgerEvent).filter(
                AuditLedgerEvent.action.in_(
                    ("manual_cycle_completed", "continuous_cycle_completed")
                ),
                AuditLedgerEvent.status == "planned",
                AuditLedgerEvent.payload_json["cycle"]["cycle_id"].astext
                == cycle_id,
            )
            row = query.order_by(AuditLedgerEvent.created_at.desc()).first()
            if row is None:
                return None
            payload = row.payload_json
            cycle = payload.get("cycle") if isinstance(payload, dict) else None
            if not isinstance(cycle, dict) or cycle.get("cycle_id") != cycle_id:
                raise OptimizationRepositoryError(
                    "O evento persistido do ciclo possui payload inválido."
                )
            created_at = getattr(row, "created_at", None)
            return {
                "audit_event_id": int(row.id),
                "persisted_at": created_at.timestamp() if created_at else None,
                "source": payload.get("source"),
                "actor_id": payload.get("actor_id"),
                "interval_seconds": payload.get("interval_seconds"),
                "trace_id": row.trace_id,
                "cycle": cycle,
            }
        except OptimizationRepositoryError:
            raise
        except Exception as exc:
            logger.exception(
                "Falha ao recuperar ciclo de otimização persistido",
                cycle_id=cycle_id,
                error=str(exc),
            )
            raise OptimizationRepositoryError(
                "Falha ao recuperar o ciclo de otimização persistido."
            ) from exc
        finally:
            session.close()


# Padrão de Injeção de Dependência: Getter para o repositório
def get_optimization_repository() -> OptimizationRepository:
    return OptimizationRepository()
