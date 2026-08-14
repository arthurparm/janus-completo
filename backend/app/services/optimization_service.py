import asyncio
import time
from enum import Enum
from typing import Any, cast

import structlog
from fastapi import HTTPException, Request, status

from app.core.agents import AgentRole
from app.core.optimization.self_optimization import (
    DetectedIssue,
    IssueSeverity,
    IssueType,
    SystemMetrics,
)
from app.core.security.actor_context import ActorContext
from app.core.security.authorization import authorization_service
from app.repositories.observability_repository import record_audit_event_direct
from app.repositories.optimization_repository import (
    OptimizationMetricsUnavailableRepositoryError,
    OptimizationRepository,
    OptimizationRepositoryError,
)
from app.repositories.prompt_repository import PromptRepository, generate_prompt_version

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---


class OptimizationServiceError(Exception):
    """Base exception for optimization service errors."""

    pass


class OptimizationExecutionUnavailableError(OptimizationServiceError):
    """A execução automática ainda não possui um adaptador verificável."""


class OptimizationMetricsUnavailableError(OptimizationServiceError):
    """Ainda não existem amostras suficientes para calcular saúde."""


class OptimizationContinuousAlreadyRunningError(OptimizationServiceError):
    """O planejador contínuo já possui uma tarefa ativa."""


class OptimizationContinuousNotRunningError(OptimizationServiceError):
    """Não existe planejador contínuo ativo para interromper."""


class OptimizationAnalysisType(str, Enum):
    """Tipos de análise que possuem implementação verificável."""

    PERFORMANCE = "performance"


# --- Optimization Service ---


class OptimizationService:
    """
    Camada de serviço para o ciclo de auto-otimização proativa.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: OptimizationRepository):
        self._repo = repo
        self._prompt_repo = PromptRepository()
        self._continuous_task: asyncio.Task[None] | None = None
        self._continuous_interval_seconds: float | None = None
        self._continuous_started_by: str | None = None
        self._continuous_trace_id: str | None = None
        self._continuous_started_at: float | None = None
        self._continuous_stopped_at: float | None = None
        self._continuous_last_error: str | None = None
        self._continuous_last_cycle_at: float | None = None
        self._continuous_last_issues_detected: int | None = None
        self._continuous_last_improvements_planned: int | None = None

    async def run_optimization_cycle(
        self,
        enable_auto_execution: bool,
        max_improvements: int | None,
        actor: ActorContext,
    ) -> dict[str, Any]:
        logger.info(
            "Orquestrando ciclo de auto-otimização via serviço", auto_execute=enable_auto_execution
        )
        self._authorize_control(actor)
        if enable_auto_execution:
            raise OptimizationExecutionUnavailableError(
                "Execução automática de melhorias não possui adaptador auditável; "
                "nenhuma melhoria foi aplicada."
            )
        try:
            result = await self._repo.run_cycle(
                enable_auto_execution=enable_auto_execution,
                max_improvements=max_improvements,
            )
            await self._persist_planning_result(
                result=result,
                actor_id=actor.actor_id,
                trace_id=actor.trace_id,
                endpoint="optimization",
                action="manual_cycle_completed",
                source="manual_rest",
            )
            return {**result, "audit_recorded": True}
        except OptimizationMetricsUnavailableRepositoryError as e:
            raise OptimizationMetricsUnavailableError(str(e)) from e
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório de otimização ao executar ciclo", exc_info=e)
            raise OptimizationServiceError("Falha ao executar o ciclo de otimização.") from e

    async def get_system_health(self) -> dict[str, Any]:
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
                "slow_tools": metrics.slow_tools,
            }
        except OptimizationMetricsUnavailableRepositoryError as e:
            raise OptimizationMetricsUnavailableError(str(e)) from e
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise OptimizationServiceError("Falha ao buscar as métricas de saúde.") from e

    async def get_detected_issues(
        self, severity: IssueSeverity | None, category: IssueType | None
    ) -> list[DetectedIssue]:
        logger.info("Orquestrando busca de problemas detectados via serviço.")
        try:
            await self._repo.get_metrics()
            issues = self._repo.find_issues()
        except OptimizationMetricsUnavailableRepositoryError as e:
            raise OptimizationMetricsUnavailableError(str(e)) from e
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório ao detectar problemas", exc_info=e)
            raise OptimizationServiceError(
                "Falha ao detectar problemas do sistema."
            ) from e

        filtered_issues = issues
        if severity is not None:
            severity_thresholds = {
                IssueSeverity.HIGH: 0.7,
                IssueSeverity.MEDIUM: 0.4,
                IssueSeverity.LOW: 0.0,
            }
            threshold = severity_thresholds[severity]
            filtered_issues = [i for i in filtered_issues if i.severity >= threshold]
        if category is not None:
            filtered_issues = [i for i in filtered_issues if i.issue_type is category]

        return filtered_issues

    async def get_metrics_history(self, limit: int) -> list[SystemMetrics]:
        logger.info("Buscando histórico de métricas via serviço.")
        if not 1 <= limit <= 100:
            raise ValueError("limit deve estar entre 1 e 100")
        history = self._repo.get_metrics_history()
        return history[-limit:]

    def _continuous_task_active(self) -> bool:
        return self._continuous_task is not None and not self._continuous_task.done()

    @staticmethod
    def _authorize_control(actor: ActorContext) -> None:
        resolved = authorization_service.require_service(actor=actor)
        if not resolved.has_scopes(("ops:execute",)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

    def _on_continuous_task_done(self, task: asyncio.Task[None]) -> None:
        outcome = "stopped"
        if task.cancelled():
            outcome = "cancelled"
        else:
            error = task.exception()
            if error is not None:
                outcome = "failed"
                if self._continuous_last_error is None:
                    self._continuous_last_error = str(error)
                logger.error(
                    "optimization_continuous_task_failed",
                    error=str(error),
                    exc_info=error,
                )
        self._continuous_stopped_at = time.time()
        if self._continuous_task is task:
            self._continuous_task = None
        record_audit_event_direct(
            endpoint="optimization_continuous",
            action="continuous_task_finished",
            status=outcome,
            user_id=self._continuous_started_by,
            details_json={
                "actor_id": self._continuous_started_by,
                "interval_seconds": self._continuous_interval_seconds,
                "error": self._continuous_last_error,
            },
        )

    async def _persist_planning_result(
        self,
        *,
        result: dict[str, Any],
        actor_id: str | None,
        trace_id: str | None,
        endpoint: str,
        action: str,
        source: str,
        interval_seconds: float | None = None,
    ) -> None:
        """Persiste um resultado de planejamento antes de confirmá-lo ao chamador."""
        try:
            recorded = await asyncio.to_thread(
                record_audit_event_direct,
                endpoint=endpoint,
                action=action,
                status="planned",
                user_id=actor_id,
                trace_id=trace_id,
                details_json={
                    "actor_id": actor_id,
                    "source": source,
                    "interval_seconds": interval_seconds,
                    "cycle": result,
                },
                required=True,
            )
        except Exception as exc:
            raise OptimizationServiceError(
                "Falha ao persistir o resultado do ciclo de otimização no ledger."
            ) from exc
        if not recorded:
            raise OptimizationServiceError(
                "O ledger não confirmou a persistência do ciclo de otimização."
            )

    async def _persist_continuous_cycle(self, result: dict[str, Any]) -> None:
        """Persiste cada resultado antes de o loop aguardar o próximo ciclo."""
        try:
            await self._persist_planning_result(
                result=result,
                actor_id=self._continuous_started_by,
                trace_id=self._continuous_trace_id,
                endpoint="optimization_continuous",
                action="continuous_cycle_completed",
                source="continuous_runtime",
                interval_seconds=self._continuous_interval_seconds,
            )
        except OptimizationServiceError as exc:
            self._continuous_last_error = (
                "Falha ao persistir o resultado do ciclo contínuo no ledger."
            )
            raise OptimizationServiceError(self._continuous_last_error) from exc
        self._continuous_last_cycle_at = time.time()
        self._continuous_last_issues_detected = int(result["issues_detected"])
        self._continuous_last_improvements_planned = int(
            result["improvements_planned"]
        )

    async def start_continuous(
        self, *, interval_seconds: float, actor: ActorContext
    ) -> dict[str, Any]:
        """Inicia planejamento periódico opt-in, sem execução automática de melhorias."""
        self._authorize_control(actor)
        if not 10 <= interval_seconds <= 86400:
            raise ValueError("interval_seconds deve estar entre 10 e 86400")
        runtime_status = self._repo.get_status()
        if self._continuous_task_active() or runtime_status.get("continuous_running"):
            raise OptimizationContinuousAlreadyRunningError(
                "O planejador contínuo de otimização já está ativo."
            )

        record_audit_event_direct(
            endpoint="optimization_continuous",
            action="continuous_start_requested",
            status="authorized",
            user_id=actor.actor_id,
            trace_id=actor.trace_id,
            details_json={
                "actor_id": actor.actor_id,
                "interval_seconds": interval_seconds,
            },
            required=True,
        )
        self._continuous_interval_seconds = interval_seconds
        self._continuous_started_by = actor.actor_id
        self._continuous_trace_id = actor.trace_id
        self._continuous_started_at = time.time()
        self._continuous_stopped_at = None
        self._continuous_last_error = None
        self._continuous_last_cycle_at = None
        self._continuous_last_issues_detected = None
        self._continuous_last_improvements_planned = None
        task = asyncio.create_task(
            self._repo.run_continuous(
                interval_seconds,
                on_cycle_completed=self._persist_continuous_cycle,
            ),
            name="janus-self-optimization-continuous",
        )
        self._continuous_task = task
        task.add_done_callback(self._on_continuous_task_done)
        await asyncio.sleep(0)
        if task.done() and self._continuous_last_error is not None:
            raise OptimizationServiceError(
                "O planejador contínuo encerrou durante a inicialização."
            )
        audit_recorded = record_audit_event_direct(
            endpoint="optimization_continuous",
            action="continuous_started",
            status="started",
            user_id=actor.actor_id,
            trace_id=actor.trace_id,
            details_json={
                "actor_id": actor.actor_id,
                "interval_seconds": interval_seconds,
            },
        )
        return {**self.get_status(), "audit_recorded": audit_recorded}

    async def _stop_continuous(
        self, *, actor: ActorContext | None, reason: str
    ) -> dict[str, Any]:
        task = self._continuous_task
        runtime_status = self._repo.get_status()
        if (task is None or task.done()) and not runtime_status.get("continuous_running"):
            raise OptimizationContinuousNotRunningError(
                "O planejador contínuo de otimização não está ativo."
            )

        actor_id = actor.actor_id if actor is not None else "janus-kernel"
        trace_id = actor.trace_id if actor is not None else None
        record_audit_event_direct(
            endpoint="optimization_continuous",
            action="continuous_stop_requested",
            status="requested",
            user_id=actor_id,
            trace_id=trace_id,
            details_json={"actor_id": actor_id, "reason": reason},
        )
        self._repo.stop_continuous()
        forced = False
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except TimeoutError:
                forced = True
            except asyncio.CancelledError:
                forced = True
            except Exception as exc:
                self._continuous_last_error = str(exc)
                logger.error(
                    "optimization_continuous_stop_failed",
                    error=str(exc),
                    exc_info=exc,
                )
        self._continuous_task = None
        self._continuous_stopped_at = time.time()
        audit_recorded = record_audit_event_direct(
            endpoint="optimization_continuous",
            action="continuous_stopped",
            status="forced" if forced else "stopped",
            user_id=actor_id,
            trace_id=trace_id,
            details_json={
                "actor_id": actor_id,
                "reason": reason,
                "forced": forced,
            },
        )
        return {
            **self.get_status(),
            "stopped": True,
            "forced": forced,
            "audit_recorded": audit_recorded,
        }

    async def stop_continuous(self, *, actor: ActorContext) -> dict[str, Any]:
        """Interrompe o planejador contínuo solicitado por um service actor."""
        self._authorize_control(actor)
        return await self._stop_continuous(actor=actor, reason="api_request")

    async def shutdown(self) -> None:
        """Interrompe a tarefa própria durante o encerramento do kernel."""
        if not self._continuous_task_active():
            return
        try:
            await self._stop_continuous(actor=None, reason="kernel_shutdown")
        except OptimizationContinuousNotRunningError:
            return

    def get_status(self) -> dict[str, Any]:
        logger.info("Buscando status do módulo de otimização via serviço.")
        status_payload = self._repo.get_status()
        task_active = self._continuous_task_active()
        runtime_running = bool(status_payload.get("continuous_running"))
        status_payload.update(
            {
                "status": (
                    "running"
                    if runtime_running
                    else "starting"
                    if task_active
                    else "idle"
                ),
                "continuous_running": runtime_running,
                "continuous_task_active": task_active,
                "continuous_control_available": True,
                "automatic_execution_available": False,
                "interval_seconds": self._continuous_interval_seconds,
                "last_started_by": self._continuous_started_by,
                "last_started_at": self._continuous_started_at,
                "last_stopped_at": self._continuous_stopped_at,
                "last_error": self._continuous_last_error,
                "last_cycle_at": self._continuous_last_cycle_at,
                "last_issues_detected": self._continuous_last_issues_detected,
                "last_improvements_planned": (
                    self._continuous_last_improvements_planned
                ),
            }
        )
        return status_payload

    async def analyze_system(
        self, analysis_type: OptimizationAnalysisType, detailed: bool
    ) -> dict[str, Any]:
        """Gera análise agregada do sistema a partir de métricas e issues."""
        try:
            normalized_analysis_type = OptimizationAnalysisType(analysis_type)
        except ValueError as exc:
            raise ValueError("analysis_type deve ser 'performance'") from exc
        logger.info(
            "Orquestrando análise do sistema via serviço.",
            analysis_type=normalized_analysis_type.value,
            detailed=detailed,
        )
        try:
            metrics = await self._repo.get_metrics()
            history = self._repo.get_metrics_history()
            issues = self._repo.find_issues()

            # Coletar séries de valores
            resp_times = [m.avg_response_time for m in history] or [metrics.avg_response_time]
            error_rates = [m.error_rate for m in history] or [metrics.error_rate]
            memory_usage = [
                value
                for item in history
                if (value := item.memory_usage_mb) is not None
            ]
            if not memory_usage and metrics.memory_usage_mb is not None:
                memory_usage = [metrics.memory_usage_mb]

            def percentile(values: list[float], p: int) -> float:
                if not values:
                    return 0.0
                s = sorted(values)
                idx = max(0, min(len(s) - 1, round(p / 100.0 * (len(s) - 1))))
                return s[idx]

            avg_response_time_p95 = round(percentile(resp_times, 95), 3)
            error_rate_avg = (
                round(sum(error_rates) / len(error_rates), 3) if error_rates else 0.0
            )
            memory_usage_latest_mb = (
                round(memory_usage[-1], 2) if memory_usage else None
            )
            memory_usage_max_mb = (
                round(max(memory_usage), 2) if memory_usage else None
            )
            trend: dict[str, Any] = {
                "avg_response_time_p95": avg_response_time_p95,
                "avg_response_time_latest": round(resp_times[-1], 3),
                "error_rate_avg": error_rate_avg,
                "memory_usage_latest_mb": memory_usage_latest_mb,
                "memory_usage_max_mb": memory_usage_max_mb,
            }

            issues_by_type: dict[str, int] = {}
            for issue in issues:
                key = issue.issue_type.value
                issues_by_type[key] = issues_by_type.get(key, 0) + 1

            insights: list[str] = []
            if avg_response_time_p95 > 2.0:
                insights.append("Latência p95 elevada (>2s). Considere otimizações de desempenho.")
            if error_rate_avg > 0.2:
                insights.append("Taxa média de erro alta (>20%). Investigue falhas recorrentes.")
            if (
                len(memory_usage) > 10
                and memory_usage_latest_mb is not None
                and memory_usage_max_mb is not None
                and memory_usage_latest_mb >= memory_usage_max_mb * 0.95
            ):
                insights.append(
                    "Uso de memória em alta persistente. Possível vazamento de memória."
                )

            analysis: dict[str, Any] = {
                "analysis_type": normalized_analysis_type.value,
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
                "series": {
                    "avg_response_time": resp_times,
                    "error_rate": error_rates,
                    "memory_usage_mb": memory_usage,
                },
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

        except OptimizationMetricsUnavailableRepositoryError as e:
            raise OptimizationMetricsUnavailableError(str(e)) from e
        except OptimizationRepositoryError as e:
            logger.error("Erro no repositório ao analisar sistema", exc_info=e)
            raise OptimizationServiceError("Falha ao analisar o sistema.") from e

    def update_agent_prompt(
        self,
        role: AgentRole,
        content: str,
        *,
        name: str | None = None,
        language: str | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        """Cria nova versão de prompt para um agente e ativa opcionalmente.
        Deriva `name` de `role` quando ausente e usa o repositório de prompts.
        """
        logger = structlog.get_logger(__name__)
        prompt_name = name or f"agent_prompt_{role.name.lower()}"
        logger.info("Atualizando prompt de agente", role=role.value, prompt_name=prompt_name)
        try:
            version_obj = self._prompt_repo.create_prompt_version(
                prompt_name=prompt_name,
                prompt_text=content,
                version=generate_prompt_version(),
                language=language or "en",
                created_by="optimization-service",
                activate=activate,
            )
            version_number = getattr(version_obj, "prompt_version", None)
            result = {
                "name": prompt_name,
                "version": version_number,
                "activated": activate,
            }
            logger.info("Prompt de agente atualizado com sucesso", **result)
            return result
        except Exception as e:
            logger.error(
                "Falha ao atualizar prompt do agente",
                role=role.value,
                prompt_name=prompt_name,
                error=str(e),
            )
            raise OptimizationServiceError("Falha ao atualizar prompt do agente.") from e


# Padrão de Injeção de Dependência: Getter para o serviço
def get_optimization_service(request: Request) -> OptimizationService:
    return cast(OptimizationService, request.app.state.optimization_service)
