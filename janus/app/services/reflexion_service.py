import time
from dataclasses import asdict, is_dataclass
from typing import Any

import structlog
from fastapi import Request

from app.core.optimization import ReflexionConfig, self_optimization_cycle
from app.repositories.reflexion_repository import ReflexionRepository, ReflexionRepositoryError

logger = structlog.get_logger(__name__)


class ReflexionServiceError(Exception):
    """Base exception for reflexion service errors."""


class ReflexionValidationError(ReflexionServiceError):
    """Raised for validation errors."""


class ReflexionTimeoutError(ReflexionServiceError):
    """Raised on execution timeout."""


class ReflexionService:
    """Camada de servico para o ciclo de auto-otimizacao Reflexion."""

    def __init__(self, repo: ReflexionRepository):
        self._repo = repo

    @staticmethod
    def _normalize_step(step: Any, position: int) -> dict[str, Any]:
        """Normaliza formatos heterogeneos de step para contrato de API estavel."""
        if is_dataclass(step):
            data = asdict(step)
        elif isinstance(step, dict):
            data = dict(step)
        elif isinstance(step, int):
            data = {"iteration": int(step)}
        else:
            data = {"iteration": position, "observation": str(step)}

        data.setdefault("iteration", position)
        data.setdefault("action", "")
        data.setdefault("observation", "")
        data.setdefault("reflection", "")
        data.setdefault("score", 0.0)
        data.setdefault("improvements", [])
        data.setdefault("timestamp", 0.0)
        return data

    async def _compute_dynamic_success_threshold(self, base: float) -> float:
        """Ajusta dinamicamente o success_threshold com base em metricas historicas."""
        try:
            metrics = await self_optimization_cycle.monitor.collect_metrics()
            health_score = self_optimization_cycle.monitor._calculate_health_score(metrics)
            adjust = (
                (health_score - 0.8) * 0.3
                - metrics.error_rate * 0.2
                - min(1.0, metrics.avg_response_time) * 0.05
            )
            dyn = max(0.6, min(0.95, base + adjust))
            logger.info(
                "Threshold dinamico calculado",
                base=base,
                adjusted=dyn,
                health_score=health_score,
                error_rate=metrics.error_rate,
                avg_response_time=metrics.avg_response_time,
            )
            return round(dyn, 2)
        except Exception as e:
            logger.warning("Falha ao calcular threshold dinamico; usando valor base.", exc_info=e)
            return base

    async def run_reflexion_cycle(
        self, task: str, config_overrides: dict[str, Any]
    ) -> dict[str, Any]:
        """Orquestra a execucao de uma tarefa com o ciclo completo de Reflexion."""
        logger.info("Orquestrando ciclo de Reflexion via servico", task=task)
        started_at = time.perf_counter()
        try:
            config = ReflexionConfig.from_settings()
            for key, value in config_overrides.items():
                if value is not None:
                    setattr(config, key, value)

            if config_overrides.get("success_threshold") is None:
                config.success_threshold = await self._compute_dynamic_success_threshold(
                    config.success_threshold
                )

            raw_result = await self._repo.run_cycle(task=task, config=config)
            if not isinstance(raw_result, dict):
                raise ValueError("Resposta invalida do ciclo Reflexion.")

            raw_steps = raw_result.get("steps", [])
            steps = [
                self._normalize_step(step, position=i + 1) for i, step in enumerate(raw_steps)
            ]
            elapsed_raw = raw_result.get("elapsed_seconds")
            elapsed_seconds = (
                round(time.perf_counter() - started_at, 2)
                if elapsed_raw is None
                else float(elapsed_raw)
            )

            result = {
                "success": bool(raw_result.get("success", False)),
                "best_result": str(raw_result.get("best_result", raw_result.get("result", "")) or ""),
                "best_score": float(
                    raw_result.get("best_score", raw_result.get("score", 0.0)) or 0.0
                ),
                "iterations": int(raw_result.get("iterations") or len(steps)),
                "lessons_learned": list(
                    raw_result.get("lessons_learned", raw_result.get("lessons", [])) or []
                ),
                "elapsed_seconds": float(elapsed_seconds),
                "steps": steps,
            }

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
            logger.error("Erro no repositorio de Reflexion", exc_info=e)
            raise ReflexionServiceError(
                "Ocorreu uma falha na camada de execucao do ciclo de Reflexion."
            ) from e
        except Exception as e:
            logger.error("Erro inesperado no servico de Reflexion", exc_info=e)
            raise ReflexionServiceError(
                "Ocorreu uma falha inesperada no servico de Reflexion."
            ) from e

    def get_config(self) -> ReflexionConfig:
        return ReflexionConfig.from_settings()

    def reset_agent_breakers(self):
        logger.info("Orquestrando reset dos circuit breakers via servico.")
        self._repo.reset_breakers()

    def get_health_status(self) -> dict[str, Any]:
        logger.info("Buscando saude do modulo Reflexion via servico.")
        return self._repo.get_health()


def get_reflexion_service(request: Request) -> ReflexionService:
    return request.app.state.reflexion_service
