import asyncio
import importlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram

from app.core.autonomy.goal_manager import Goal, GoalManager, GoalStatus
from app.core.autonomy.planner import build_plan_for_goal
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine
from app.core.infrastructure.realtime import get_realtime_service
from app.core.tools.action_module import action_registry
from app.repositories.autonomy_repository import AutonomyRepository
from app.services.llm_service import LLMService
from app.services.optimization_service import OptimizationService

logger = structlog.get_logger(__name__)


# === Métricas Prometheus ===
AUTONOMY_CYCLES = Counter(
    "autonomy_loop_cycles_total", "Total de ciclos do AutonomyLoop", ["outcome"]
)

AUTONOMY_LATENCY = Histogram(
    "autonomy_loop_cycle_duration_seconds", "Duração dos ciclos do AutonomyLoop"
)

AUTONOMY_ACTIONS = Counter(
    "autonomy_loop_actions_total", "Ações executadas pelo AutonomyLoop", ["outcome"]
)

AUTONOMY_ACTIVE = Gauge("autonomy_loop_active", "Indicador se o loop de autonomia está ativo")


class AutonomyServiceError(Exception):
    """Erro base para o serviço de autonomia."""

    pass


@dataclass
class AutonomyConfig:
    interval_seconds: int = 60
    user_id: str | None = None
    project_id: str | None = None
    risk_profile: str = "balanced"
    auto_confirm: bool = False
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)
    max_actions_per_cycle: int = 20
    max_seconds_per_cycle: int = 60
    plan: list[dict[str, Any]] = field(default_factory=list)


class AutonomyService:
    """Serviço AutonomyLoop básico: Perceber → Planejar → Executar → Refletir → Otimizar."""

    def __init__(
        self,
        optimization_service: OptimizationService,
        llm_service: LLMService | None = None,
        goal_manager: GoalManager | None = None,
        repo: AutonomyRepository | None = None,
    ):
        self._optimization_service = optimization_service
        self._llm_service = llm_service
        self._goal_manager = goal_manager
        self._config = AutonomyConfig()
        # Safe-by-default: require explicit approval before action execution.
        self._policy = PolicyEngine(PolicyConfig(auto_confirm=False))
        self._autonomy_task: asyncio.Task | None = None
        self._running = False
        self._cycle_count = 0
        self._last_cycle_at: float | None = None
        self._repo = repo or AutonomyRepository()
        self._current_run_id: int | None = None
        self._core_tools_bootstrapped = False

    def _ensure_core_tools_registered(self) -> None:
        """Carrega agent_tools uma vez para disparar o registro no action_registry."""
        if self._core_tools_bootstrapped and action_registry.get_tool("get_current_datetime"):
            return
        try:
            importlib.import_module("app.core.tools.agent_tools")
            self._core_tools_bootstrapped = True
        except Exception as e:
            logger.warning(
                "[AutonomyLoop] Falha ao carregar registro de ferramentas base",
                exc_info=e,
            )

    def _is_active(self) -> bool:
        return self._autonomy_task is not None and not self._autonomy_task.done()

    async def start(self, config: AutonomyConfig) -> bool:
        if self._is_active():
            logger.warning("Tentativa de iniciar AutonomyLoop já ativo.")
            return False
        self._config = config
        self._policy = PolicyEngine(
            PolicyConfig(
                risk_profile=config.risk_profile,
                auto_confirm=config.auto_confirm,
                allowlist=set(config.allowlist or []),
                blocklist=set(config.blocklist or []),
                max_actions_per_cycle=config.max_actions_per_cycle,
                max_seconds_per_cycle=config.max_seconds_per_cycle,
            )
        )
        self._running = True
        AUTONOMY_ACTIVE.set(1)
        self._ensure_core_tools_registered()

        try:
            existing_run = self._repo.get_active_run(
                user_id=self._config.user_id, project_id=self._config.project_id
            )
            if existing_run:
                self._current_run_id = existing_run.id
                self._cycle_count = int(existing_run.cycles or 0)
                logger.info(
                    "AutonomyLoop restaurado de run existente",
                    run_id=existing_run.id,
                    cycles_restored=self._cycle_count,
                )
            else:
                run = self._repo.create_run(
                    user_id=self._config.user_id,
                    project_id=self._config.project_id,
                    risk_profile=self._config.risk_profile,
                    auto_confirm=self._config.auto_confirm,
                    allowlist=self._config.allowlist,
                    blocklist=self._config.blocklist,
                    max_actions_per_cycle=self._config.max_actions_per_cycle,
                    max_seconds_per_cycle=self._config.max_seconds_per_cycle,
                    interval_seconds=self._config.interval_seconds,
                )
                self._current_run_id = run.id
                logger.info("AutonomyLoop nova run criada", run_id=run.id)
        except Exception as e:
            logger.warning("Erro ao recuperar/criar run de autonomia", exc_info=e)
            self._current_run_id = None

        self._autonomy_task = asyncio.create_task(self._run_loop())
        logger.info("AutonomyLoop iniciado", interval_seconds=config.interval_seconds)
        return True

    async def stop(self) -> bool:
        if not self._is_active():
            logger.warning("Tentativa de parar AutonomyLoop inativo.")
            return False
        self._running = False
        AUTONOMY_ACTIVE.set(0)

        if self._autonomy_task:
            self._autonomy_task.cancel()
            try:
                await self._autonomy_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Erro ao cancelar tarefa de autonomia", exc_info=e)

        try:
            if self._current_run_id:
                self._repo.stop_run(self._current_run_id)
        except Exception as e:
            logger.warning("Erro ao finalizar run no repositório", exc_info=e)

        logger.info("AutonomyLoop parado")
        return True

    def get_status(self) -> dict[str, Any]:
        return {
            "active": self._is_active(),
            "cycle_count": self._cycle_count,
            "last_cycle_at": self._last_cycle_at,
            "config": {
                "interval_seconds": self._config.interval_seconds,
                "risk_profile": self._config.risk_profile,
                "auto_confirm": self._config.auto_confirm,
                "max_actions_per_cycle": self._config.max_actions_per_cycle,
                "max_seconds_per_cycle": self._config.max_seconds_per_cycle,
                "allowlist": self._config.allowlist,
                "blocklist": self._config.blocklist,
                "user_id": self._config.user_id,
                "project_id": self._config.project_id,
                "plan": self._config.plan,
            },
        }

    def update_plan(self, plan: list[dict[str, Any]]) -> None:
        self._config.plan = plan or []
        logger.info("Plano de execução atualizado", steps=len(self._config.plan))

    def update_policy_config(
        self,
        risk_profile: str | None = None,
        auto_confirm: bool | None = None,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
        max_actions_per_cycle: int | None = None,
        max_seconds_per_cycle: int | None = None,
    ) -> None:
        if risk_profile is not None:
            self._config.risk_profile = risk_profile
        if auto_confirm is not None:
            self._config.auto_confirm = bool(auto_confirm)
        if allowlist is not None:
            self._config.allowlist = allowlist or []
        if blocklist is not None:
            self._config.blocklist = blocklist or []
        if isinstance(max_actions_per_cycle, int) and max_actions_per_cycle > 0:
            self._config.max_actions_per_cycle = max_actions_per_cycle
        if isinstance(max_seconds_per_cycle, int) and max_seconds_per_cycle > 0:
            self._config.max_seconds_per_cycle = max_seconds_per_cycle

        self._policy = PolicyEngine(
            PolicyConfig(
                risk_profile=self._config.risk_profile,
                auto_confirm=self._config.auto_confirm,
                allowlist=set(self._config.allowlist or []),
                blocklist=set(self._config.blocklist or []),
                max_actions_per_cycle=self._config.max_actions_per_cycle,
                max_seconds_per_cycle=self._config.max_seconds_per_cycle,
            )
        )
        logger.info(
            "Configuração de políticas atualizada",
            risk_profile=self._config.risk_profile,
            auto_confirm=self._config.auto_confirm,
        )

    async def _run_loop(self):
        try:
            while self._running:
                start_t = time.perf_counter()
                outcome = "success"
                try:
                    await self._run_cycle()
                except Exception as e:
                    outcome = "failure"
                    logger.error("Falha no ciclo do AutonomyLoop", exc_info=e)
                finally:
                    duration = time.perf_counter() - start_t
                    AUTONOMY_CYCLES.labels(outcome).inc()
                    AUTONOMY_LATENCY.observe(duration)
                    self._cycle_count += 1
                    self._last_cycle_at = time.time()

                try:
                    if self._current_run_id:
                        self._repo.increment_cycles(self._current_run_id)
                except Exception as e:
                    logger.warning("Falha ao incrementar ciclos no repositório", exc_info=e)

                await asyncio.sleep(max(1, int(self._config.interval_seconds)))
        except asyncio.CancelledError:
            logger.info("Tarefa de AutonomyLoop cancelada")
        except Exception as e:
            logger.error("Erro fatal não tratado no AutonomyLoop", exc_info=e)

    async def _run_cycle(self):
        # Perceber: Métricas de saúde
        metrics = await self._optimization_service.get_system_health()
        logger.info("[AutonomyLoop] Perceber: métricas", **metrics)

        # Realtime: Status & Metrics
        try:
            rt = get_realtime_service()
            rt.broadcast_status("thinking", "Analisando sistema e metas...")
            rt.broadcast_metrics(
                cpu=metrics.get("cpu_percent", 0), memory=metrics.get("memory_percent", 0)
            )
        except Exception as e:
            logger.warning("Falha ao comunicar com RealtimeService", exc_info=e)
            # Não aborta, é secundário

        # Seleciona meta atual (se disponível)
        current_goal: Goal | None = None
        try:
            if self._goal_manager:
                current_goal = self._goal_manager.get_next_goal()
                if current_goal and current_goal.status == GoalStatus.PENDING:
                    self._goal_manager.update_goal_status(current_goal.id, GoalStatus.IN_PROGRESS)
        except Exception as e:
            logger.error("Erro ao buscar/atualizar meta no GoalManager", exc_info=e)
            current_goal = None

        # Planejar
        if self._config.plan:
            plan = self._config.plan
        else:
            plan = []
            if current_goal and self._llm_service:
                try:
                    rt.append_log(f"Gerando plano para meta: {current_goal.title}", "info")
                    plan = await build_plan_for_goal(
                        goal=current_goal,
                        metrics=metrics,
                        llm_service=self._llm_service,
                        policy=self._policy,
                        max_steps=self._config.max_actions_per_cycle,
                        timeout_seconds=max(5, self._config.max_seconds_per_cycle),
                    )
                except Exception as e:
                    logger.error("[AutonomyLoop] Falha ao gerar plano via planner", exc_info=e)
                    rt.append_log(f"Falha no planejador: {e!s}", "error")

            if not plan:
                plan = [
                    {"tool": "get_current_datetime", "args": {}},
                    {"tool": "get_system_info", "args": {}},
                ]

        # Executar
        self._ensure_core_tools_registered()
        self._policy.reset_cycle_quota()

        for step_idx, step in enumerate(plan):
            if not self._policy.can_continue_cycle():
                logger.info("[AutonomyLoop] Quotas do ciclo atingidas; interrompendo execução")
                break

            tool_name = step.get("tool")
            args = step.get("args", {})
            critical = step.get("critical", True)
            max_retries = step.get("retry", 0)
            fallback_tool_name = step.get("fallback_tool")

            step_success = False
            attempts = 0

            while attempts <= max_retries:
                attempts += 1

                # Validação de Policy
                decision = self._policy.validate_tool_call(tool_name, args)
                if not decision.allowed:
                    logger.warning(
                        "[AutonomyLoop] Ação bloqueada", tool=tool_name, reason=decision.reason
                    )
                    AUTONOMY_ACTIONS.labels("blocked").inc()
                    break

                if decision.require_confirmation:
                    try:
                        import json as _json
                        from app.repositories.pending_action_repository import (
                            PendingActionRepository,
                        )

                        par = PendingActionRepository()
                        par.create(
                            user_id=str(self._config.user_id or ""),
                            tool_name=tool_name,
                            args_json=_json.dumps(args, ensure_ascii=False),
                            run_id=self._current_run_id,
                            cycle=self._cycle_count + 1,
                        )
                        AUTONOMY_ACTIONS.labels("blocked").inc()
                        logger.info("[AutonomyLoop] Ação enviada para aprovação", tool=tool_name)
                    except Exception as e:
                        logger.error(
                            "Falha ao criar Ação Pendente! Interrompendo passo.", exc_info=e
                        )
                        rt.append_log("Erro crítico ao solicitar aprovação.", "error")
                        # Se não conseguiu salvar a pendência, não podemos pausar nem continuar.
                        # Falha crítica técnica.

                    # Seja sucesso ou falha ao salvar, interrompemos o fluxo desse passo
                    # (se salvou, espera user. se falhou, aborta).
                    step_success = True  # "Sucesso" lógico pois foi pausado
                    break

                tool = action_registry.get_tool(tool_name)
                if not tool:
                    logger.warning("[AutonomyLoop] Ferramenta não encontrada", tool=tool_name)
                    AUTONOMY_ACTIONS.labels("error").inc()
                    break

                # Execução Real
                t0 = time.perf_counter()
                success = False
                error_msg = None
                input_preview = ""
                result_preview = ""

                try:
                    # Payload Prep
                    try:
                        if getattr(tool, "args_schema", None):
                            payload = args or {}
                        elif isinstance(args, dict) and "tool_input" in args:
                            payload = args["tool_input"]
                        else:
                            payload = "" if not args else json.dumps(args, ensure_ascii=False)
                    except Exception as e:
                        logger.warning("log_warning", message=f"Erro ao preparar payload para {tool_name}", exc_info=e)
                        payload = args

                    rt.broadcast_status(
                        "executing",
                        f"Executando: {tool_name} (Tentativa {attempts}/{max_retries + 1})",
                    )
                    rt.append_log(f"Executando: {tool_name}", "info")

                    # Invoke
                    # Ferramentas sem args (ex.: get_current_datetime) quebram quando recebem
                    # payload posicional vazio (""). Para args={} preferimos invoke/ainvoke({})
                    # e mantemos o comportamento legado para payloads não vazios.
                    if isinstance(args, dict) and not args:
                        if hasattr(tool, "ainvoke"):
                            result = await tool.ainvoke({})
                        elif hasattr(tool, "invoke"):
                            result = tool.invoke({})
                        else:
                            result = (
                                await tool.arun(payload) if hasattr(tool, "arun") else tool.run(payload)
                            )
                    else:
                        result = (
                            await tool.arun(payload) if hasattr(tool, "arun") else tool.run(payload)
                        )
                    success = True
                    step_success = True

                    # Log Formatting (Safe)
                    payload_str = str(payload)
                    input_preview = payload_str[:300]
                    result_str = str(result)
                    result_preview = result_str[:500]

                    logger.info(
                        "[AutonomyLoop] Ação executada com sucesso",
                        tool=tool_name,
                        attempt=attempts,
                        result_preview=result_preview,
                    )
                    AUTONOMY_ACTIONS.labels("success").inc()

                except Exception as e:
                    success = False
                    error_msg = str(e)
                    logger.error(
                        "[AutonomyLoop] Erro na execução",
                        tool=tool_name,
                        attempt=attempts,
                        exc_info=e,
                    )
                    AUTONOMY_ACTIONS.labels("error").inc()
                finally:
                    dur = time.perf_counter() - t0
                    try:
                        action_registry.record_call(
                            tool_name, dur, success=success, error=error_msg, input_args=args
                        )
                    except Exception as e:
                        logger.warning("Falha ao registrar métrica no ActionRegistry", exc_info=e)

                    try:
                        if self._current_run_id is not None:
                            self._repo.add_step(
                                run_id=self._current_run_id,
                                cycle=self._cycle_count + 1,
                                tool=tool_name,
                                input_preview=input_preview or str(args),
                                input_length=len(input_preview or ""),
                                result_preview=result_preview or error_msg or "",
                                result_length=len(result_preview or error_msg or ""),
                                success=success,
                                error=error_msg,
                                duration_seconds=dur,
                            )
                    except Exception as e:
                        logger.warning("Falha ao registrar passo no histórico", exc_info=e)

                if success:
                    break  # Sai do loop de retries

                if attempts <= max_retries:
                    logger.info("log_info", message=f"[AutonomyLoop] Retentando {tool_name} em 2s...")
                    await asyncio.sleep(2)

            # Fallback & Replanning logic...
            if not step_success:
                logger.error("log_error", message=f"[AutonomyLoop] Passo falhou definitivamente: {tool_name}")

                if fallback_tool_name:
                    logger.info("log_info", message=f"[AutonomyLoop] Tentando fallback: {fallback_tool_name}")
                    fallback_tool = action_registry.get_tool(fallback_tool_name)
                    if fallback_tool:
                        try:
                            # Tenta fallback (sem retries complexos por enquanto)
                            if isinstance(args, dict) and not args:
                                if hasattr(fallback_tool, "ainvoke"):
                                    fallback_res = await fallback_tool.ainvoke({})
                                elif hasattr(fallback_tool, "invoke"):
                                    fallback_res = fallback_tool.invoke({})
                                else:
                                    fallback_res = (
                                        await fallback_tool.arun(args)
                                        if hasattr(fallback_tool, "arun")
                                        else fallback_tool.run(args)
                                    )
                            else:
                                fallback_res = (
                                    await fallback_tool.arun(args)
                                    if hasattr(fallback_tool, "arun")
                                    else fallback_tool.run(args)
                                )
                            logger.info("log_info", message=f"[AutonomyLoop] Fallback executado com sucesso")
                            step_success = True
                        except Exception as e:
                            logger.error("log_error", message=f"[AutonomyLoop] Fallback falhou: {e}")
                            error_msg = f"Primary and Fallback failed. Last error: {e!s}"

            # Dynamic Replanning
            if step_success and critical and current_goal and self._llm_service:
                try:
                    from app.core.autonomy.planner import verify_outcome

                    verification = await verify_outcome(
                        current_goal,
                        step,
                        result if "result" in locals() else None,
                        None,
                        self._llm_service,
                    )
                    if not verification.get("success", True):
                        logger.warning("log_warning", message=f"[AutonomyLoop] Verificação semântica falhou: {verification.get('reason')}"
                        )
                        rt.append_log(
                            f"Resultado rejeitado: {verification.get('reason')}", "warning"
                        )
                        step_success = False
                        error_msg = f"Semantic Verification Failed: {verification.get('reason')}"
                except Exception as e_ver:
                    logger.error("Erro na verificação semântica", exc_info=e_ver)

            if not step_success and critical:
                logger.warning("log_warning", message=f"[AutonomyLoop] Falha crítica em {tool_name}. Iniciando REPLANNING..."
                )
                rt.append_log("Falha crítica. Replanejando...", "warning")

                if not current_goal or not self._llm_service:
                    logger.warning(
                        "[AutonomyLoop] Meta ou LLM ausente; não é possível replanejar."
                    )
                    break

                goal_for_replan = current_goal
                llm_for_replan = self._llm_service

                try:
                    from app.core.autonomy.planner import replan_goal

                    replan_decision = await replan_goal(
                        goal=goal_for_replan,
                        failed_step=step,
                        error_msg=str(error_msg),
                        remaining_steps=plan[step_idx + 1 :],
                        llm_service=llm_for_replan,
                        policy=self._policy,
                    )

                    action = replan_decision.get("action", "ABORT")
                    logger.info("log_info", message=f"[AutonomyLoop] Decisão de Replanejamento: {action}")

                    if action == "IGNORE":
                        rt.append_log("Falha ignorada pelo replanejador.", "info")
                        continue
                    elif action == "RETRY_WITH_ARGS":
                        new_args = replan_decision.get("new_args", {})
                        rt.append_log("Retentando com novos parâmetros...", "info")
                        retry_step = step.copy()
                        retry_step["args"] = new_args
                        retry_step["retry"] = 0
                        plan.insert(step_idx + 1, retry_step)
                        continue
                    elif action == "NEW_PLAN":
                        new_steps = replan_decision.get("new_steps", [])
                        if new_steps:
                            rt.append_log("Novo plano adotado.", "success")
                            del plan[step_idx + 1 :]
                            plan.extend(new_steps)
                            continue
                        else:
                            break
                    elif action == "ABORT":
                        rt.append_log("Replanejador abortou a meta.", "error")
                        break
                except Exception as e_replan:
                    logger.error(
                        "Erro crítico no sistema de Replanejamento", exc_info=e_replan
                    )
                    break

                break


# --- Dependency Injection Helper ---
def get_autonomy_service(request: Request) -> "AutonomyService":
    return request.app.state.autonomy_service
