import asyncio
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


@dataclass
class AutonomyConfig:
    interval_seconds: int = 60
    user_id: str | None = None
    project_id: str | None = None
    risk_profile: str = "balanced"
    auto_confirm: bool = True
    allowlist: list[str] = field(default_factory=list)
    blocklist: list[str] = field(default_factory=list)
    max_actions_per_cycle: int = 20
    max_seconds_per_cycle: int = 60
    plan: list[dict[str, Any]] = field(default_factory=list)


class AutonomyService:
    """Serviço AutonomyLoop básico: Perceber → Planejar → Executar → Refletir → Otimizar.

    Nesta versão inicial, o loop coleta métricas do sistema (Perceber),
    registra um plano simplificado de diagnóstico (Planejar) e executa ações
    seguras do ActionRegistry respeitando PolicyEngine (Executar).
    Fechamento de loop (Refletir/Otimizar) será integrado em etapas seguintes.
    """

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
        self._policy = PolicyEngine(PolicyConfig())
        self._autonomy_task: asyncio.Task | None = None
        self._running = False
        self._cycle_count = 0
        self._last_cycle_at: float | None = None
        self._repo = repo or AutonomyRepository()
        self._current_run_id: int | None = None

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

        # Tenta restaurar uma run ativa existente (ex: após reinício do container)
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
                # Cria nova run se não houver ativa
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
        try:
            self._autonomy_task.cancel()
        except Exception:
            pass
        try:
            if self._current_run_id:
                self._repo.stop_run(self._current_run_id)
        except Exception:
            pass
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
        """Atualiza o plano de execução usado nos ciclos seguintes.

        A alteração é aplicada imediatamente a `self._config.plan` e será
        utilizada no próximo `_run_cycle`. Não reinicia o loop.
        """
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
            allowlist=len(self._config.allowlist),
            blocklist=len(self._config.blocklist),
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
                    logger.error("Falha no ciclo de AutonomyLoop", exc_info=e)
                finally:
                    duration = time.perf_counter() - start_t
                    AUTONOMY_CYCLES.labels(outcome).inc()
                    AUTONOMY_LATENCY.observe(duration)
                    self._cycle_count += 1
                    self._last_cycle_at = time.time()
                try:
                    if self._current_run_id:
                        self._repo.increment_cycles(self._current_run_id)
                except Exception:
                    pass
                await asyncio.sleep(max(1, int(self._config.interval_seconds)))
        except asyncio.CancelledError:
            logger.info("Tarefa de AutonomyLoop cancelada")
        except Exception as e:
            logger.error("Erro inesperado no AutonomyLoop", exc_info=e)

    async def _run_cycle(self):
        # Perceber: Métricas de saúde
        metrics = await self._optimization_service.get_system_health()
        logger.info("[AutonomyLoop] Perceber: métricas", **metrics)

        # Realtime: Status & Metrics
        rt = get_realtime_service()
        rt.broadcast_status("thinking", "Analisando sistema e metas...")
        rt.broadcast_metrics(
            cpu=metrics.get("cpu_percent", 0), memory=metrics.get("memory_percent", 0)
        )

        # Seleciona meta atual (se disponível)
        current_goal: Goal | None = None
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

        # Executar: respeitando PolicyEngine e rate limits
        self._policy.reset_cycle_quota()

        for step_idx, step in enumerate(plan):
            if not self._policy.can_continue_cycle():
                logger.info("[AutonomyLoop] Quotas do ciclo atingidas; interrompendo execução")
                break

            # Robust Planning Metadata
            tool_name = step.get("tool")
            args = step.get("args", {})
            critical = step.get("critical", True)
            max_retries = step.get("retry", 0)
            fallback_tool_name = step.get("fallback_tool")

            # Execução do passo com retries e fallback
            step_success = False
            attempts = 0

            # Loop de Tentativas (Original + Retries)
            while attempts <= max_retries:
                attempts += 1

                # Validação de Policy
                decision = self._policy.validate_tool_call(tool_name, args)
                if not decision.allowed:
                    logger.warning(
                        "[AutonomyLoop] Ação bloqueada", tool=tool_name, reason=decision.reason
                    )
                    AUTONOMY_ACTIONS.labels("blocked").inc()
                    # Bloqueio de policy é falha terminal para este passo, não adianta retry
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
                    except Exception:
                        pass
                    # Ação pendente conta como sucesso parcial (não falhou, apenas pausou)
                    # Mas para o planner, interrompemos fluxo imediato
                    step_success = True
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
                    # Preparar payload
                    payload = None
                    try:
                        if getattr(tool, "args_schema", None):
                            payload = args or {}
                        elif isinstance(args, dict) and "tool_input" in args:
                            payload = args["tool_input"]
                        else:
                            payload = "" if not args else json.dumps(args, ensure_ascii=False)
                    except Exception:
                        payload = "" if not args else json.dumps(args, ensure_ascii=False)

                    # Log & Broadcast
                    rt.broadcast_status(
                        "executing",
                        f"Executando: {tool_name} (Tentativa {attempts}/{max_retries + 1})",
                    )
                    rt.append_log(f"Executando: {tool_name}", "info")

                    # RUN
                    result = (
                        await tool.arun(payload) if hasattr(tool, "arun") else tool.run(payload)
                    )
                    success = True
                    step_success = True

                    # Formatting output for logs
                    try:
                        payload_str = (
                            payload
                            if isinstance(payload, str)
                            else json.dumps(payload, ensure_ascii=False)
                        )
                    except Exception:
                        payload_str = str(payload)
                    input_preview = payload_str[:300]
                    input_length = len(payload_str)

                    try:
                        result_str = (
                            result
                            if isinstance(result, str)
                            else json.dumps(result, ensure_ascii=False)
                        )
                    except Exception:
                        result_str = str(result)
                    result_preview = result_str[:500]
                    result_length = len(result_str)

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
                    # Telemetria
                    dur = time.perf_counter() - t0
                    try:
                        action_registry.record_call(
                            tool_name, dur, success=success, error=error_msg, input_args=args
                        )
                    except Exception:
                        pass
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
                    except Exception:
                        pass

                if success:
                    break  # Sai do loop de retries

                # Se falhou e ainda tem retries, wait before retry
                if attempts <= max_retries:
                    logger.info(f"[AutonomyLoop] Retentando {tool_name} em 2s...")
                    await asyncio.sleep(2)

            # Fim do loop de retries. Se falhou todas as vezes:
            if not step_success:
                logger.error(f"[AutonomyLoop] Passo falhou definitivamente: {tool_name}")

                # Tenta Fallback se existir (Lógica Local Rapid Recovery)
                if fallback_tool_name:
                    logger.info(f"[AutonomyLoop] Tentando fallback: {fallback_tool_name}")
                    fallback_tool = action_registry.get_tool(fallback_tool_name)
                    if fallback_tool:
                        try:
                            fallback_res = (
                                await fallback_tool.arun(args)
                                if hasattr(fallback_tool, "arun")
                                else fallback_tool.run(args)
                            )
                            logger.info(
                                f"[AutonomyLoop] Fallback {fallback_tool_name} executado com sucesso"
                            )
                            step_success = True  # Recuperado pelo fallback
                        except Exception as e:
                            logger.error(f"[AutonomyLoop] Fallback também falhou: {e}")
                            error_msg = f"Primary and Fallback failed. Last error: {e!s}"

                # Se falhou (mesmo após fallback) e é crítico -> DYNAMIC REPLANNING (SOTA)
                # [NEW] SEMANTIC VERIFICATION: Mesmo se step_success=True, verificar se o output presta.
                if step_success and critical:
                    try:
                        from app.core.autonomy.planner import verify_outcome

                        verification = await verify_outcome(
                            current_goal,
                            step,
                            result if "result" in locals() else None,
                            None,
                            self._llm_service,
                        )  # type: ignore
                        if not verification.get("success", True):
                            logger.warning(
                                f"[AutonomyLoop] Verificação semântica falhou: {verification.get('reason')}"
                            )
                            rt.append_log(
                                f"Resultado rejeitado: {verification.get('reason')}", "warning"
                            )
                            step_success = False  # Força falha para triggerar replanning
                            error_msg = (
                                f"Semantic Verification Failed: {verification.get('reason')}"
                            )
                    except Exception as e_ver:
                        logger.error("Erro na verificação semântica", exc_info=e_ver)

                if not step_success and critical:
                    logger.warning(
                        f"[AutonomyLoop] Falha crítica em {tool_name}. Iniciando REPLANNING..."
                    )
                    rt.append_log("Falha crítica. Replanejando...", "warning")

                    try:
                        from app.core.autonomy.planner import replan_goal

                        # Calcula passos restantes
                        remaining = plan[step_idx + 1 :]

                        replan_decision = await replan_goal(
                            goal=current_goal,  # type: ignore
                            failed_step=step,
                            error_msg=str(error_msg),
                            remaining_steps=remaining,
                            llm_service=self._llm_service,  # type: ignore
                            policy=self._policy,
                        )

                        action = replan_decision.get("action", "ABORT")
                        logger.info(f"[AutonomyLoop] Decisão de Replanejamento: {action}")

                        if action == "IGNORE":
                            logger.info("Replanejador decidiu ignorar falha. Continuando.")
                            rt.append_log("Falha ignorada pelo replanejador.", "info")
                            continue  # Vai para o próximo passo do loop for

                        elif action == "RETRY_WITH_ARGS":
                            new_args = replan_decision.get("new_args", {})
                            logger.info(
                                "Replanejador sugeriu novos argumentos. Retentando...",
                                new_args=new_args,
                            )
                            rt.append_log("Retentando com novos parâmetros...", "info")
                            # Modifica o passo atual e reseta tentativas - hack elegante:
                            # Não podemos resetar o 'enumerate', mas podemos executar in-place agora ou
                            # inserir um novo passo na lista? A lista 'plan' é iterável.
                            # Melhor: Executar recursivamente/diretamente agora.
                            # Simplificação: Apenas logamos que vamos tentar na proxima iteração?
                            # Não, o loop já passou. Vamos inserir na posição seguinte do plano e continuar?
                            # Mas queremos executar AGORA.
                            # Solução: Inserir na lista 'plan' na posição step_idx + 1 e continuar loop
                            # Assim o 'for' vai pegar ele na próxima iteração.
                            retry_step = step.copy()
                            retry_step["args"] = new_args
                            retry_step["retry"] = 0  # Um retry já basta
                            # Inserimos logo a frente
                            plan.insert(step_idx + 1, retry_step)
                            continue

                        elif action == "NEW_PLAN":
                            new_steps = replan_decision.get("new_steps", [])
                            if new_steps:
                                logger.info(
                                    f"Replanejador gerou novo plano com {len(new_steps)} passos."
                                )
                                rt.append_log("Novo plano adotado.", "success")
                                # Atualiza o plano self._config.plan SE quisermos persistir
                                # Mas aqui estamos num loop local 'plan'.
                                # Vamos substituir os passos restantes.
                                # Python permite modificar lista enquanto itera SE tivermos cuidado,
                                # mas 'enumerate' usa iterador. Modificar lista futura pode ser tricky.
                                # Mais seguro: Truncar lista atual e estender.
                                del plan[step_idx + 1 :]  # Remove restantes antigos
                                plan.extend(new_steps)  # Adiciona novos
                                # O loop for vai continuar, consumindo os novos passos
                                continue
                            else:
                                logger.warning(
                                    "Replanejador sugeriu NEW_PLAN mas enviou lista vazia. Abortando."
                                )
                                break

                        elif action == "ABORT":
                            logger.error("Replanejador decidiu ABORTAR.")
                            rt.append_log("Replanejador abortou a meta.", "error")
                            break

                    except Exception as e_replan:
                        logger.error("Erro crítico no sistema de Replanejamento", exc_info=e_replan)
                        rt.append_log(f"Erro no replanejador: {e_replan!s}", "error")
                        break

                    logger.error(
                        "[AutonomyLoop] Passo crítico falhou e replanejamento não recuperou. Abortando."
                    )
                    break


# --- Dependency Injection Helper ---
def get_autonomy_service(request: Request) -> "AutonomyService":
    return request.app.state.autonomy_service
