from dataclasses import asdict
from typing import Any

import structlog
from fastapi import Request

from app.core.optimization import ReflexionConfig, self_optimization_cycle
from app.repositories.reflexion_repository import ReflexionRepository, ReflexionRepositoryError

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---


class ReflexionServiceError(Exception):
    """Base exception for reflexion service errors."""

    pass


class ReflexionValidationError(ReflexionServiceError):
    """Raised for validation errors."""

    pass


class ReflexionTimeoutError(ReflexionServiceError):
    """Raised on execution timeout."""

    pass


# --- Reflexion Service ---


class ReflexionService:
    """
    Camada de serviço para o ciclo de auto-otimização Reflexion.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: ReflexionRepository):
        self._repo = repo

    async def _compute_dynamic_success_threshold(self, base: float) -> float:
        """Ajusta dinamicamente o success_threshold com base em métricas históricas."""
        try:
            metrics = await self_optimization_cycle.monitor.collect_metrics()
            health_score = self_optimization_cycle.monitor._calculate_health_score(metrics)
            # Ajuste leve em torno do baseline: sobe quando o sistema está saudável, desce quando há degradação
            adjust = (
                (health_score - 0.8) * 0.3
                - metrics.error_rate * 0.2
                - min(1.0, metrics.avg_response_time) * 0.05
            )
            dyn = max(0.6, min(0.95, base + adjust))
            logger.info(
                "Threshold dinâmico calculado",
                base=base,
                adjusted=dyn,
                health_score=health_score,
                error_rate=metrics.error_rate,
                avg_response_time=metrics.avg_response_time,
            )
            return round(dyn, 2)
        except Exception as e:
            logger.warning("Falha ao calcular threshold dinâmico; usando valor base.", exc_info=e)
            return base

    async def run_reflexion_cycle(
        self, task: str, config_overrides: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Orquestra a execução de uma tarefa com o ciclo completo de Reflexion.
        """
        logger.info("Orquestrando ciclo de Reflexion via serviço", task=task)
        try:
            config = ReflexionConfig.from_settings()
            for key, value in config_overrides.items():
                if value is not None:
                    setattr(config, key, value)

            # Aplicar ajuste dinâmico quando não houver override explícito do usuário
            if config_overrides.get("success_threshold") is None:
                config.success_threshold = await self._compute_dynamic_success_threshold(
                    config.success_threshold
                )

            result = await self._repo.run_cycle(task=task, config=config)

            result["steps"] = [asdict(step) for step in result.get("steps", [])]
            result["iterations"] = len(result["steps"])

            logger.info(
                "Ciclo de Reflexion orquestrado com sucesso",
                success=result["success"],
                score=result["best_score"],
            )
            return result
        except ValueError as e:
            raise ReflexionValidationError(str(e)) from e
        except TimeoutError as e:
            raise ReflexionTimeoutError(str(e)) from e
        except ReflexionRepositoryError as e:
            logger.error("Erro no repositório de Reflexion", exc_info=e)
            raise ReflexionServiceError(
                "Ocorreu uma falha na camada de execução do ciclo de Reflexion."
            ) from e
        except Exception as e:
            logger.error("Erro inesperado no serviço de Reflexion", exc_info=e)
            raise ReflexionServiceError(
                "Ocorreu uma falha inesperada no serviço de Reflexion."
            ) from e

    def get_config(self) -> ReflexionConfig:
        return ReflexionConfig.from_settings()

    def reset_agent_breakers(self):
        logger.info("Orquestrando reset dos circuit breakers via serviço.")
        self._repo.reset_breakers()

    def get_health_status(self) -> dict[str, Any]:
        logger.info("Buscando saúde do módulo Reflexion via serviço.")
        return self._repo.get_health()


# Padrão de Injeção de Dependência: Getter para o serviço
def get_reflexion_service(request: Request) -> ReflexionService:
    return request.app.state.reflexion_service
