import asyncio
import importlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog
from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram

from app.core.autonomy.goal_manager import Goal, GoalManager, GoalStatus
from app.core.autonomy.planner import build_plan_for_goal
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine
from app.core.tools.action_module import action_registry
from app.models.schemas import TaskState, TaskStateEvent
from app.repositories.autonomy_repository import AutonomyRepository
from app.services.collaboration_service import CollaborationService
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
    execution_mode: Literal["enqueue_router"] = "enqueue_router"
    plan: list[dict[str, Any]] = field(default_factory=list)


class AutonomyService:
    """Serviço AutonomyLoop básico: Perceber → Planejar → Executar → Refletir → Otimizar."""

    def __init__(
        self,
        optimization_service: OptimizationService,
        llm_service: LLMService | None = None,
        goal_manager: GoalManager | None = None,
        repo: AutonomyRepository | None = None,
        collaboration_service: CollaborationService | None = None,
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
        self._collaboration_service = collaboration_service
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
        logger.info(
            "AutonomyLoop iniciado",
            interval_seconds=config.interval_seconds,
            execution_mode=self._config.execution_mode,
        )
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
                "execution_mode": self._config.execution_mode,
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

    async def _perceive_metrics(self) -> dict[str, Any]:
        metrics = await self._optimization_service.get_system_health()
        logger.info("[AutonomyLoop] Perceber: métricas", **metrics)
        return metrics

    def _select_goal(self) -> Goal | None:
        current_goal: Goal | None = None
        try:
            if self._goal_manager:
                current_goal = self._goal_manager.get_next_goal()
                if current_goal and current_goal.status == GoalStatus.PENDING:
                    self._goal_manager.update_goal_status(current_goal.id, GoalStatus.IN_PROGRESS)
        except Exception as e:
            logger.error("Erro ao buscar/atualizar meta no GoalManager", exc_info=e)
            current_goal = None
        return current_goal

    async def _build_plan(self, current_goal: Goal | None, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        if self._config.plan:
            return self._config.plan

        if current_goal and self._llm_service:
            try:
                return await build_plan_for_goal(
                    goal=current_goal,
                    metrics=metrics,
                    llm_service=self._llm_service,
                    policy=self._policy,
                    max_steps=self._config.max_actions_per_cycle,
                    timeout_seconds=max(5, self._config.max_seconds_per_cycle),
                )
            except Exception as e:
                logger.error("[AutonomyLoop] Falha ao gerar plano via planner", exc_info=e)

        return [
            {"tool": "get_current_datetime", "args": {}},
            {"tool": "get_system_info", "args": {}},
        ]

    def _select_step_for_enqueue(self, plan: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not plan:
            return None
        preferred = ("search_web", "get_enriched_context")
        for step in plan:
            try:
                if str(step.get("tool", "")) in preferred:
                    return step
            except Exception:
                continue
        return plan[-1]

    def _to_original_goal_text(self, goal: Goal, step: dict[str, Any]) -> str:
        tool = str(step.get("tool", "")).strip()
        args = step.get("args", {}) or {}
        if tool == "search_web":
            q = args.get("query") or args.get("q") or goal.title
            return f"Pesquisar '{q}' no Tavily"
        if tool == "get_enriched_context":
            topic = args.get("topic") or goal.title
            return f"Obter contexto enriquecido sobre '{topic}'"
        if tool == "get_system_info":
            return "Coletar informações do sistema"
        if tool == "get_current_datetime":
            return "Obter data/hora atual"
        cleaned = json.dumps(args, ensure_ascii=False)
        return f"Executar '{tool}' com argumentos {cleaned}"

    def _record_history_step(
        self,
        *,
        cycle: int,
        tool: str,
        input_preview: str,
        result_preview: str,
        success: bool,
        error: str | None,
        duration_seconds: float,
    ) -> None:
        try:
            if self._current_run_id is None:
                return
            self._repo.add_step(
                run_id=self._current_run_id,
                cycle=cycle,
                tool=tool,
                input_preview=input_preview,
                input_length=len(input_preview or ""),
                result_preview=result_preview or "",
                result_length=len(result_preview or ""),
                success=success,
                error=error,
                duration_seconds=duration_seconds,
            )
        except Exception as e:
            logger.warning("Falha ao registrar passo no histórico", exc_info=e)

    async def _enqueue_taskstate(
        self,
        *,
        goal: Goal,
        metrics: dict[str, Any],
        plan: list[dict[str, Any]],
        step: dict[str, Any],
    ) -> str:
        if not self._collaboration_service:
            raise AutonomyServiceError("CollaborationService ausente para modo enqueue_router")

        original_goal = self._to_original_goal_text(goal, step)
        task_state = TaskState(
            original_goal=original_goal,
            next_agent_role="router",
            data_payload={
                # Contract v1 for enqueue-first autonomy context (auditoria/contexto)
                "autonomy": {
                    "goal": {
                        "id": goal.id,
                        "title": goal.title,
                        "description": goal.description,
                        "priority": goal.priority,
                    },
                    "metrics": metrics,
                    "plan": plan,
                    "selected_step": step,
                    "mode": "enqueue_router",
                    "autonomy_run_id": self._current_run_id,
                }
            },
            history=[
                TaskStateEvent(
                    agent_role="autonomy",
                    action="auto_enqueue",
                    notes=f"Gerado do objetivo '{goal.title}'",
                )
            ],
            meta={
                "source": "autonomy_loop",
                "autonomy": {
                    "goal_id": goal.id,
                    "execution_mode": "enqueue_router",
                    "autonomy_run_id": self._current_run_id,
                },
            },
        )
        await self._collaboration_service.pass_task(task_state)
        logger.info(
            "[AutonomyLoop] TaskState auto-enfileirado",
            task_id=task_state.task_id,
            goal=goal.title,
            next_role=task_state.next_agent_role,
        )
        return task_state.task_id

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
        await self._run_cycle_enqueue()

    async def _run_cycle_enqueue(self):
        cycle = self._cycle_count + 1
        current_goal: Goal | None = None
        step_name = ""
        step_t0 = time.perf_counter()
        try:
            metrics = await self._perceive_metrics()
            current_goal = self._select_goal()
            if not current_goal:
                logger.info("[AutonomyLoop] Nenhuma meta pendente para enfileirar")
                self._record_history_step(
                    cycle=cycle,
                    tool="autonomy_enqueue",
                    input_preview="no_goal",
                    result_preview="Nenhuma meta pendente",
                    success=True,
                    error=None,
                    duration_seconds=time.perf_counter() - step_t0,
                )
                return

            plan = await self._build_plan(current_goal, metrics)
            step = self._select_step_for_enqueue(plan)
            if not step:
                logger.info("[AutonomyLoop] Plano vazio no modo enqueue_router")
                self._record_history_step(
                    cycle=cycle,
                    tool="autonomy_enqueue",
                    input_preview=f"goal={current_goal.id}",
                    result_preview="Plano vazio",
                    success=False,
                    error="empty_plan",
                    duration_seconds=time.perf_counter() - step_t0,
                )
                return

            step_name = str(step.get("tool", "")).strip()
            task_id = await self._enqueue_taskstate(
                goal=current_goal,
                metrics=metrics,
                plan=plan,
                step=step,
            )
            input_preview = (
                f"goal={current_goal.id}:{current_goal.title[:80]} "
                f"selected_tool={step_name or 'unknown'}"
            )[:300]
            result_preview = (
                f"task_id={task_id} next_agent_role=router selected_tool={step_name or 'unknown'}"
            )[:500]
            self._record_history_step(
                cycle=cycle,
                tool="autonomy_enqueue",
                input_preview=input_preview,
                result_preview=result_preview,
                success=True,
                error=None,
                duration_seconds=time.perf_counter() - step_t0,
            )
        except Exception as e:
            if current_goal:
                try:
                    self._goal_manager.update_goal_status(current_goal.id, GoalStatus.PENDING)
                except Exception:
                    pass
            self._record_history_step(
                cycle=cycle,
                tool="autonomy_enqueue",
                input_preview=(
                    f"goal={getattr(current_goal, 'id', 'none')} selected_tool={step_name or 'unknown'}"
                )[:300],
                result_preview=str(e)[:500],
                success=False,
                error=str(e),
                duration_seconds=time.perf_counter() - step_t0,
            )
            raise

# --- Dependency Injection Helper ---
def get_autonomy_service(request: Request) -> "AutonomyService":
    return request.app.state.autonomy_service
