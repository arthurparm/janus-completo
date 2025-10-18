import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import structlog
from prometheus_client import Counter, Histogram, Gauge

from app.core.autonomy.policy_engine import PolicyEngine, PolicyConfig
from app.services.optimization_service import OptimizationService
from app.core.tools.action_module import action_registry
from fastapi import Request

# NEW IMPORTS
from app.services.llm_service import LLMService
from app.core.autonomy.goal_manager import GoalManager, GoalStatus, Goal
from app.core.autonomy.planner import build_plan_for_goal

logger = structlog.get_logger(__name__)


# === Métricas Prometheus ===
AUTONOMY_CYCLES = Counter(
    "autonomy_loop_cycles_total",
    "Total de ciclos do AutonomyLoop",
    ["outcome"]
)

AUTONOMY_LATENCY = Histogram(
    "autonomy_loop_cycle_duration_seconds",
    "Duração dos ciclos do AutonomyLoop"
)

AUTONOMY_ACTIONS = Counter(
    "autonomy_loop_actions_total",
    "Ações executadas pelo AutonomyLoop",
    ["outcome"]
)

AUTONOMY_ACTIVE = Gauge(
    "autonomy_loop_active",
    "Indicador se o loop de autonomia está ativo"
)


@dataclass
class AutonomyConfig:
    interval_seconds: int = 60
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    risk_profile: str = "balanced"
    auto_confirm: bool = True
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)
    max_actions_per_cycle: int = 20
    max_seconds_per_cycle: int = 60
    plan: list[Dict[str, Any]] = field(default_factory=list)


class AutonomyService:
    """Serviço AutonomyLoop básico: Perceber → Planejar → Executar → Refletir → Otimizar.

    Nesta versão inicial, o loop coleta métricas do sistema (Perceber),
    registra um plano simplificado de diagnóstico (Planejar) e executa ações
    seguras do ActionRegistry respeitando PolicyEngine (Executar).
    Fechamento de loop (Refletir/Otimizar) será integrado em etapas seguintes.
    """

    def __init__(self, optimization_service: OptimizationService, llm_service: Optional[LLMService] = None, goal_manager: Optional[GoalManager] = None):
        self._optimization_service = optimization_service
        self._llm_service = llm_service
        self._goal_manager = goal_manager
        self._config = AutonomyConfig()
        self._policy = PolicyEngine(PolicyConfig())
        self._autonomy_task: Optional[asyncio.Task] = None
        self._running = False
        self._cycle_count = 0
        self._last_cycle_at: Optional[float] = None

    def _is_active(self) -> bool:
        return self._autonomy_task is not None and not self._autonomy_task.done()

    async def start(self, config: AutonomyConfig) -> bool:
        if self._is_active():
            logger.warning("Tentativa de iniciar AutonomyLoop já ativo.")
            return False
        self._config = config
        self._policy = PolicyEngine(PolicyConfig(
            risk_profile=config.risk_profile,
            auto_confirm=config.auto_confirm,
            allowlist=set(config.allowlist or []),
            blocklist=set(config.blocklist or []),
            max_actions_per_cycle=config.max_actions_per_cycle,
            max_seconds_per_cycle=config.max_seconds_per_cycle,
        ))
        self._running = True
        AUTONOMY_ACTIVE.set(1)
        self._autonomy_task = asyncio.create_task(self._run_loop())
        logger.info("AutonomyLoop iniciado", interval_seconds=config.interval_seconds)
        return True

    async def stop(self) -> bool:
        if not self._is_active():
            logger.warning("Tentativa de parar AutonomyLoop inativo.")
            return False
        self._running = False
        AUTONOMY_ACTIVE.set(0)
        try:
            self._autonomy_task.cancel()
        except Exception:
            pass
        logger.info("AutonomyLoop parado")
        return True

    def get_status(self) -> Dict[str, Any]:
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
            }
        }

    def update_plan(self, plan: list[Dict[str, Any]]) -> None:
        """Atualiza o plano de execução usado nos ciclos seguintes.

        A alteração é aplicada imediatamente a `self._config.plan` e será
        utilizada no próximo `_run_cycle`. Não reinicia o loop.
        """
        self._config.plan = plan or []
        logger.info("Plano de execução atualizado", steps=len(self._config.plan))

    async def _run_loop(self):
        try:
            while self._running:
                start_t = time.perf_counter()
                outcome = "success"
                try:
                    await self._run_cycle()
                except Exception as e:
                    outcome = "failure"
                    logger.error("Falha no ciclo de AutonomyLoop", exc_info=e)
                finally:
                    duration = time.perf_counter() - start_t
                    AUTONOMY_CYCLES.labels(outcome).inc()
                    AUTONOMY_LATENCY.observe(duration)
                    self._cycle_count += 1
                    self._last_cycle_at = time.time()
                await asyncio.sleep(max(1, int(self._config.interval_seconds)))
        except asyncio.CancelledError:
            logger.info("Tarefa de AutonomyLoop cancelada")
        except Exception as e:
            logger.error("Erro inesperado no AutonomyLoop", exc_info=e)

    async def _run_cycle(self):
        # Perceber: Métricas de saúde
        metrics = await self._optimization_service.get_system_health()
        logger.info("[AutonomyLoop] Perceber: métricas", **metrics)

        # Seleciona meta atual (se disponível)
        current_goal: Optional[Goal] = None
        try:
            if self._goal_manager:
                current_goal = self._goal_manager.get_next_goal()
                if current_goal and current_goal.status == GoalStatus.PENDING:
                    self._goal_manager.update_goal_status(current_goal.id, GoalStatus.IN_PROGRESS)
        except Exception:
            current_goal = None

        # Planejar: se houver plano na configuração usa; caso contrário, gera via Planner
        if self._config.plan:
            plan = self._config.plan
        else:
            plan = []
            if current_goal and self._llm_service:
                try:
                    plan = await build_plan_for_goal(
                        goal=current_goal,
                        metrics=metrics,
                        llm_service=self._llm_service,
                        policy=self._policy,
                        max_steps=self._config.max_actions_per_cycle,
                        timeout_seconds=max(5, self._config.max_seconds_per_cycle)
                    )
                except Exception as e:
                    logger.error("[AutonomyLoop] Falha ao gerar plano via planner", exc_info=e)
            if not plan:
                plan = [
                    {"tool": "get_current_datetime", "args": {}},
                    {"tool": "get_system_info", "args": {}},
                ]

        # Executar: respeitando PolicyEngine e rate limits
        self._policy.reset_cycle_quota()
        for step in plan:
            if not self._policy.can_continue_cycle():
                logger.info("[AutonomyLoop] Quotas do ciclo atingidas; interrompendo execução")
                break
            tool_name = step["tool"]
            args = step.get("args", {})
            decision = self._policy.validate_tool_call(tool_name, args)
            if not decision.allowed:
                logger.warning("[AutonomyLoop] Ação bloqueada", tool=tool_name, reason=decision.reason)
                AUTONOMY_ACTIONS.labels("blocked").inc()
                continue
            tool = action_registry.get_tool(tool_name)
            if not tool:
                logger.warning("[AutonomyLoop] Ferramenta não encontrada", tool=tool_name)
                AUTONOMY_ACTIONS.labels("error").inc()
                continue
            t0 = time.perf_counter()
            success = False
            error_msg = None
            try:
                # Determina payload de entrada conforme tipo de ferramenta
                # Ferramentas simples (@tool) normalmente esperam 'tool_input' (string)
                # Ferramentas estruturadas (StructuredTool) aceitam dict via args_schema
                payload = None
                try:
                    if getattr(tool, "args_schema", None):
                        # structured input
                        payload = args or {}
                    else:
                        # single input
                        if isinstance(args, dict) and "tool_input" in args:
                            payload = args["tool_input"]
                        else:
                            payload = "" if not args else json.dumps(args, ensure_ascii=False)
                except Exception:
                    payload = "" if not args else json.dumps(args, ensure_ascii=False)

                result = await tool.arun(payload) if hasattr(tool, "arun") else tool.run(payload)
                # Logging aprimorado: preview + tamanho de entrada e saída
                try:
                    payload_str = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
                except Exception:
                    payload_str = str(payload)
                input_preview = payload_str[:300]
                input_length = len(payload_str)
                try:
                    result_str = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                except Exception:
                    result_str = str(result)
                result_preview = result_str[:500]
                result_length = len(result_str)
                logger.info("[AutonomyLoop] Ação executada",
                            tool=tool_name,
                            input_preview=input_preview,
                            input_length=input_length,
                            result_preview=result_preview,
                            result_length=result_length)
                AUTONOMY_ACTIONS.labels("success").inc()
                success = True
            except Exception as e:
                # Inclui preview da entrada no erro para facilitar depuração
                try:
                    payload_str = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
                except Exception:
                    payload_str = str(payload)
                logger.error("[AutonomyLoop] Erro ao executar ação",
                             tool=tool_name,
                             input_preview=payload_str[:300],
                             exc_info=e)
                AUTONOMY_ACTIONS.labels("error").inc()
                error_msg = str(e)
            finally:
                # Telemetria da ferramenta via ActionRegistry já é capturada no registro dos próprios tools
                dur = time.perf_counter() - t0
                try:
                    action_registry.record_call(tool_name, dur, success=success, error=error_msg, input_args=args)
                except Exception:
                    pass


# --- Dependency Injection Helper ---
def get_autonomy_service(request: Request) -> "AutonomyService":
    return request.app.state.autonomy_service