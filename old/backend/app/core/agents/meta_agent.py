"""
Meta-Agente de Auto-Otimização - A Consciência Proativa do Janus (Sprint 13).

O Meta-Agente é um supervisor autônomo que monitora continuamente a saúde
e eficiência do ecossistema Janus, identificando padrões de falha e propondo
melhorias sem intervenção humana.
"""

import asyncio
import json
import structlog
import uuid
import time
import re
from datetime import datetime
from typing import Any

try:
    from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable
except ImportError:
    DeadlineExceeded = type("DeadlineExceeded", (Exception,), {})
    ServiceUnavailable = type("ServiceUnavailable", (Exception,), {})

from prometheus_client import Counter, Gauge, Histogram

from app.core.agents.meta_agent_module.schemas import (
    IssueSeverity,
    IssueCategory,
    DetectedIssue,
    Recommendation,
    StateReport,
    AgentState,
    ReflexionAnalysisSchema,
    DiagnosisSchema,
    PlanSchema,
    CritiqueSchema,
    safe_issue_severity,
    safe_issue_category,
)
from app.core.agents.meta_agent_module.graph_builder import MetaAgentGraphBuilder
from app.core.memory.working_memory import get_working_memory
from app.core.agents.meta_agent_module.tools import (
    analyze_memory_for_failures,
    get_system_health_metrics,
    analyze_performance_trends,
    get_resource_usage,
)

from app.core.agents.multi_agent_system import MultiAgentSystem
from app.core.agents.structures import AgentRole, Task, TaskPriority
from app.core.agents.utils import parse_json_lenient
from app.config import settings
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm.router import ModelPriority, ModelRole, get_llm

logger = structlog.get_logger(__name__)

# --- Métricas ---
META_AGENT_CYCLES = Counter(
    "meta_agent_cycles_total", "Total de ciclos executados pelo Meta-Agente", ["outcome"]
)

META_AGENT_ISSUES_DETECTED = Counter(
    "meta_agent_issues_detected_total",
    "Total de problemas detectados pelo Meta-Agente",
    ["severity", "category"],
)

META_AGENT_RECOMMENDATIONS = Counter(
    "meta_agent_recommendations_total", "Total de recomendações geradas", ["category"]
)

META_AGENT_CYCLE_DURATION = Histogram(
    "meta_agent_cycle_duration_seconds", "Duração do ciclo do Meta-Agente"
)

META_AGENT_HEALTH_SCORE = Gauge(
    "meta_agent_perceived_health_score", "Score de saúde percebido pelo Meta-Agente (0-100)"
)


META_AGENT_CYCLE_INFLIGHT = Gauge(
    "meta_agent_cycle_inflight", "Quantidade de ciclos do Meta-Agente em execucao"
)

META_AGENT_CYCLE_SKIPPED = Counter(
    "meta_agent_cycle_skipped_total",
    "Total de ciclos ignorados por controle de eficiencia",
    ["reason"],
)


class MetaAgentError(Exception):
    """Erro interno do Meta-Agente."""

    pass


class MetaAgentRetryStrategy:
    @staticmethod
    def is_retryable_error(exception):
        return isinstance(exception, (ServiceUnavailable, DeadlineExceeded))


class MetaAgent:
    """
    Meta-Agente de Auto-Otimização do Janus (LangGraph-Based).
    Supervisor autônomo com consciência diagnóstica e loop de reflexão.
    """

    def __init__(self):
        self.agent_id = "meta_agent_supervisor"
        self.tools = [
            analyze_memory_for_failures,
            get_system_health_metrics,
            analyze_performance_trends,
            get_resource_usage,
        ]
        self.llm = None
        self.executor = None
        # Init LangGraph
        self.graph_builder = MetaAgentGraphBuilder(self)
        self.app = self.graph_builder.build()

        self.last_report: StateReport | None = None
        self.cycle_count = 0
        self._heartbeat_task: asyncio.Task | None = None
        self._cycle_lock = asyncio.Lock()
        self._last_cycle_started_at = 0.0
        self._min_cycle_interval_seconds = int(
            getattr(settings, "META_AGENT_MIN_CYCLE_INTERVAL_SECONDS", 30)
        )
        # self._initialize_agent() called lazily

    async def _initialize_agent(self):
        try:
            self.llm = await get_llm(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY
            )
            logger.info("Meta-Agente (LangGraph) inicializado com sucesso.")
        except Exception as e:
            logger.warning("log_warning", message=f"Meta-Agente iniciou sem LLM: {e}")
            self.llm = None

    async def run_analysis_cycle(
        self, trigger: dict[str, Any] | None = None, force: bool = False
    ) -> StateReport:
        """Entry point do ciclo (via LangGraph), com controle de concorrencia/cooldown."""
        trigger = trigger or {}
        now = time.time()

        if self._cycle_lock.locked() and not force:
            META_AGENT_CYCLE_SKIPPED.labels("busy").inc()
            logger.info("log_info", message=f"Meta-Agent cycle skipped: busy (trigger={trigger})")
            if self.last_report is not None:
                return self.last_report
            return self._create_skipped_report("busy")

        elapsed = now - self._last_cycle_started_at
        if (not force) and self._last_cycle_started_at and elapsed < self._min_cycle_interval_seconds:
            META_AGENT_CYCLE_SKIPPED.labels("cooldown").inc()
            remaining = self._min_cycle_interval_seconds - elapsed
            logger.info("log_info", message=f"Meta-Agent cycle skipped: cooldown (remaining_seconds={remaining:.2f}, trigger={trigger})"
            )
            if self.last_report is not None:
                return self.last_report
            return self._create_skipped_report("cooldown")

        async with self._cycle_lock:
            META_AGENT_CYCLE_INFLIGHT.inc()
            self._last_cycle_started_at = time.time()
            cycle_start = time.perf_counter()
            try:
                if not self.llm:
                    await self._initialize_agent()
                if not self.llm:
                    return self._create_error_report("LLM Unavailable")

                cycle_id = f"cycle_{self.cycle_count}_{int(datetime.now().timestamp())}"
                self.cycle_count += 1

                initial_state: AgentState = {
                    "cycle_id": cycle_id,
                    "timestamp": datetime.now().timestamp(),
                    "metrics": {},
                    "detected_issues": [],
                    "diagnosis": "",
                    "candidate_plan": [],
                    "critique": None,
                    "final_plan": [],
                    "execution_results": [],
                    "status": "idle",
                    "retry_count": 0,
                    "max_retries": 3,
                }

                config = {"configurable": {"thread_id": "meta_agent_main_thread"}}
                final_state_dict = await self.app.ainvoke(initial_state, config=config)

                report = self._state_dict_to_report(final_state_dict)
                self.last_report = report
                META_AGENT_CYCLES.labels("success").inc()
                self._log_report(report)
                return report
            except Exception as e:
                logger.error("log_error", message=f"Erro fatal no LangGraph do Meta-Agente: {e}", exc_info=True)
                return self._create_error_report(str(e))
            finally:
                META_AGENT_CYCLE_DURATION.observe(time.perf_counter() - cycle_start)
                META_AGENT_CYCLE_INFLIGHT.dec()

    async def start_heartbeat(self, interval_minutes: int = 60) -> bool:
        """Inicia o heartbeat do meta-agente com ciclos periódicos."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return False
        interval_seconds = max(30, int(interval_minutes) * 60)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval_seconds))
        logger.info("log_info", message=f"Meta-Agent heartbeat iniciado (interval_seconds={interval_seconds})")
        return True

    def stop_heartbeat(self) -> None:
        """Interrompe o heartbeat do meta-agente."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = None
        logger.info("Meta-Agent heartbeat parado")

    async def _heartbeat_loop(self, interval_seconds: int) -> None:
        """Loop de execução periódica do meta-agente."""
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.run_analysis_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Erro no heartbeat do Meta-Agent", exc_info=e)
                await asyncio.sleep(min(60, interval_seconds))

    # --- Core Logic (Adapted for Dict State) ---

    def _llm_supports_structured_output(self, llm: Any) -> bool:
        try:
            base_url = str(getattr(llm, "openai_api_base", "") or getattr(llm, "base_url", ""))
        except Exception:
            base_url = ""
        if "deepseek" in base_url.lower():
            return False
        return True

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        if not content:
            return {}
        try:
            parsed = parse_json_lenient(content)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"items": parsed}
        except Exception as exc:
            logger.warning("log_warning", message=f"Failed to parse JSON response: {exc}")
        return {}

    def _extract_response_text(self, response: Any) -> str:
        return str(getattr(response, "content", response))

    def _coerce_critique_from_text(self, raw_text: str) -> dict[str, Any]:
        if not raw_text:
            return {}
        match = re.search(r"approved\s*[:=]\s*(true|false)", raw_text, re.IGNORECASE)
        if not match:
            return {}
        approved = match.group(1).lower() == "true"
        return {
            "approved": approved,
            "reason": "Coerced from non-JSON critique output.",
            "safe_subset_ids": [],
        }

    def _heuristic_critique(self, plan: list[dict[str, Any]]) -> dict[str, Any]:
        if not plan:
            return {"approved": False, "reason": "Empty plan", "safe_subset_ids": []}
        text = json.dumps(plan).lower()
        risky_markers = [
            "rm -rf",
            "drop",
            "truncate",
            "delete",
            "format",
            "wipe",
            "destroy",
            "shutdown",
            "rollback",
            "reset",
        ]
        if any(marker in text for marker in risky_markers):
            return {
                "approved": False,
                "reason": "Heuristic critique: risky action detected.",
                "safe_subset_ids": [],
            }
        return {
            "approved": True,
            "reason": "Heuristic critique: plan appears safe and actionable.",
            "safe_subset_ids": [],
        }

    async def monitor_node_logic(self, state: AgentState) -> dict:
        """Coleta métricas e identifica anomalias iniciais."""
        logger.info("[MetaAgent] Node: Monitor")
        try:
            results = await asyncio.gather(
                asyncio.to_thread(get_system_health_metrics.invoke, {}),
                analyze_memory_for_failures.ainvoke({"time_window_hours": 24, "max_results": 20}),
                asyncio.to_thread(get_resource_usage.invoke, {}),
            )

            metrics = {"health": results[0], "failures": results[1], "resources": results[2]}

            # Simple heuristic detection
            issues = []
            try:
                health_data = (
                    json.loads(metrics["health"]) if isinstance(metrics["health"], str) else {}
                )
                fail_data = (
                    json.loads(metrics["failures"]) if isinstance(metrics["failures"], str) else {}
                )

                if health_data.get("system_health", {}).get("status") != "healthy":
                    issues.append(
                        {
                            "id": f"health_{datetime.now().timestamp()}",
                            "severity": IssueSeverity.HIGH.value,
                            "category": IssueCategory.RELIABILITY.value,
                            "title": "System Health Degraded",
                            "description": f"Health monitor reports status: {health_data.get('system_health', {}).get('status')}",
                            "evidence": health_data.get("system_health", {}),
                            "detected_at": datetime.now().isoformat(),
                        }
                    )

                if fail_data.get("status") == "failures_found":
                    issues.append(
                        {
                            "id": f"failures_{datetime.now().timestamp()}",
                            "severity": IssueSeverity.MEDIUM.value,
                            "category": IssueCategory.RELIABILITY.value,
                            "title": "Recent Action Failures Detected",
                            "description": f"Detected {fail_data.get('total_failures')} failures in last 24h.",
                            "evidence": fail_data,
                            "detected_at": datetime.now().isoformat(),
                        }
                    )

            except Exception as e:
                logger.warning("log_warning", message=f"Error parsing metrics for heuristic check: {e}")

            return {"metrics": metrics, "detected_issues": issues}

        except Exception as e:
            logger.error("log_error", message=f"Error in monitor node: {e}", exc_info=True)
            return {"metrics": {"error": str(e)}}

    async def diagnosis_node_logic(self, state: AgentState) -> dict:
        """Usa LLM para diagnosticar a causa raiz dos problemas."""
        logger.info("[MetaAgent] Node: Diagnose")
        issues = state.get("detected_issues", [])
        if not issues:
            return {"diagnosis": "No issues to diagnose."}

        prompt = await get_formatted_prompt(
            "meta_agent_diagnosis",
            issues=json.dumps(issues, indent=2),
            metrics=json.dumps(state.get("metrics", {}), indent=2),
        )

        try:
            assert self.llm is not None

            try:
                if self._llm_supports_structured_output(self.llm):
                    structured_llm = self.llm.with_structured_output(DiagnosisSchema)
                    diag_result = await structured_llm.ainvoke(prompt)

                    if hasattr(diag_result, "root_cause"):
                        return {"diagnosis": diag_result.root_cause}
                    if isinstance(diag_result, dict):
                        return {"diagnosis": diag_result.get("root_cause", str(diag_result))}
                    return {"diagnosis": str(diag_result)}

                response = await self.llm.ainvoke(prompt)
                raw_text = self._extract_response_text(response)
                parsed = self._parse_json_response(raw_text)
                if parsed.get("root_cause"):
                    return {"diagnosis": parsed["root_cause"]}
                return {"diagnosis": raw_text}
            except Exception as parse_err:
                logger.warning("log_warning", message=f"Structured output failed for diagnosis: {parse_err}. Falling back to raw."
                )
                response = await self.llm.ainvoke(prompt)
                raw_text = self._extract_response_text(response)
                parsed = self._parse_json_response(raw_text)
                if parsed.get("root_cause"):
                    return {"diagnosis": parsed["root_cause"]}
                return {"diagnosis": raw_text}
        except Exception as e:
            logger.error("log_error", message=f"Error in diagnosis node: {e}", exc_info=True)
            return {"diagnosis": f"Diagnosis failed: {e}"}

    async def planning_node_logic(self, state: AgentState) -> dict:
        """Gera um plano de ação (recomendações)."""
        logger.info("[MetaAgent] Node: Plan")
        diagnosis = state.get("diagnosis", "")

        prompt = await get_formatted_prompt(
            "meta_agent_planning",
            diagnosis=diagnosis,
            issues=json.dumps(state.get("detected_issues", []), indent=2),
        )

        try:
            assert self.llm is not None

            try:
                if self._llm_supports_structured_output(self.llm):
                    structured_llm = self.llm.with_structured_output(PlanSchema)
                    plan_result = await structured_llm.ainvoke(prompt)

                    recommendations = []
                    if hasattr(plan_result, "recommendations"):
                        recommendations = [rec.dict() for rec in plan_result.recommendations]
                    elif isinstance(plan_result, dict):
                        recommendations = plan_result.get("recommendations", [])

                    if not recommendations:
                        raise ValueError("Empty recommendations from structured plan")
                    return {"candidate_plan": recommendations}

                response = await self.llm.ainvoke(prompt)
                raw_text = self._extract_response_text(response)
                parsed = self._parse_json_response(raw_text)
                recommendations = parsed.get("recommendations")
                if not isinstance(recommendations, list) or not recommendations:
                    raise ValueError("No recommendations found in JSON response")
                return {"candidate_plan": recommendations}

            except Exception as parse_err:
                logger.warning("log_warning", message=f"Structured output failed for plan: {parse_err}")
                return {
                    "candidate_plan": [
                        {
                            "title": "Manual Investigation (Fallback)",
                            "description": "Meta Agent failed to generate structured plan.",
                            "priority": 1,
                            "suggested_agent": "sysadmin",
                        }
                    ]
                }
        except Exception as e:
            logger.error("log_error", message=f"Error in planning node: {e}", exc_info=True)
            return {"candidate_plan": []}

    async def reflection_node_logic(self, state: AgentState) -> dict:
        """Critica o plano candidato."""
        logger.info("[MetaAgent] Node: Reflect")
        plan = state.get("candidate_plan", [])
        if not plan:
            return {
                "critique": {"approved": False, "reason": "Empty plan"},
                "status": "retry",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        prompt = await get_formatted_prompt(
            "meta_agent_reflection",
            plan=json.dumps(plan, indent=2),
            diagnosis=state.get("diagnosis", ""),
        )

        try:
            assert self.llm is not None

            try:
                if self._llm_supports_structured_output(self.llm):
                    structured_llm = self.llm.with_structured_output(CritiqueSchema)
                    critique_result = await structured_llm.ainvoke(prompt)

                    critique_dict = (
                        critique_result.dict()
                        if hasattr(critique_result, "dict")
                        else critique_result
                    )
                    if not isinstance(critique_dict, dict):
                        critique_dict = {"approved": False, "reason": "Invalid critique structure"}

                    if critique_dict.get("approved"):
                        return {"critique": critique_dict, "final_plan": plan, "status": "approved"}
                    return {
                        "critique": critique_dict,
                        "status": "retry",
                        "retry_count": state.get("retry_count", 0) + 1,
                    }

                response = await self.llm.ainvoke(prompt)
                raw_text = self._extract_response_text(response)
                critique_dict = self._parse_json_response(raw_text)
                if not critique_dict:
                    critique_dict = self._coerce_critique_from_text(raw_text)
                if not critique_dict:
                    critique_dict = self._heuristic_critique(plan)
                    logger.warning(
                        "Critique parsing failed; using heuristic critique fallback."
                    )

                if critique_dict.get("approved"):
                    return {"critique": critique_dict, "final_plan": plan, "status": "approved"}
                return {
                    "critique": critique_dict,
                    "status": "retry",
                    "retry_count": state.get("retry_count", 0) + 1,
                }
            except Exception as parse_err:
                logger.warning("log_warning", message=f"Structured critique failed: {parse_err}")
                critique_fallback = self._heuristic_critique(plan)
                if critique_fallback.get("approved"):
                    return {
                        "critique": critique_fallback,
                        "final_plan": plan,
                        "status": "approved",
                    }
                return {
                    "critique": critique_fallback,
                    "status": "retry",
                    "retry_count": state.get("retry_count", 0) + 1,
                }
        except Exception as e:
            logger.error("log_error", message=f"Error in reflection node: {e}", exc_info=True)
            return {
                "critique": {"approved": False, "reason": f"Error: {e}"},
                "status": "retry",
                "retry_count": state.get("retry_count", 0) + 1,
            }

    async def execution_node_logic(self, state: AgentState) -> dict:
        """Simula execução (ou despacha para outros agentes)."""
        logger.info("[MetaAgent] Node: Execute")
        plan = state.get("final_plan", [])
        results = []
        failed = 0

        try:
            for rec in plan:
                result = await self._dispatch_task(rec, state)
                results.append(result)
                if result.get("status") not in ("completed", "queued", "dispatched"):
                    failed += 1
                logger.info(
                    "Recommendation executed",
                    extra={
                        "title": rec.get("title"),
                        "status": result.get("status"),
                        "agent_role": result.get("agent_role"),
                    },
                )

                META_AGENT_RECOMMENDATIONS.labels(rec.get("category", "general")).inc()

            META_AGENT_CYCLES.labels("success").inc()
            return {
                "execution_results": results,
                "status": "completed" if failed == 0 else "partial",
            }

        except Exception as e:
            logger.error("log_error", message=f"[MetaAgent] Execution Failed: {e}", exc_info=True)
            return {
                "execution_error": str(e),
                "status": "execution_failed",
            }

    async def error_reflexion_node_logic(self, state: AgentState) -> dict:
        """
        Nó de Reflexion & Self-Correction (Shinn et al., 2023).
        Analisa a falha, gera insights e armazena na memória de curto prazo.
        """
        logger.info("[MetaAgent] Node: Error Reflexion")
        error_msg = state.get("execution_error", "Unknown error")
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if retry_count >= max_retries:
            logger.warning("Max retries reached in Reflexion.")
            return {"status": "give_up"}

        # 1. Analisar Erro com LLM
        prompt = await get_formatted_prompt(
            "reflexion_analysis",
            error=error_msg,
            plan=json.dumps(state.get("final_plan", []), indent=2),
            context=state.get("diagnosis", "No context"),
        )

        try:
            llm = await get_llm(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY)
            if self._llm_supports_structured_output(llm):
                structured_llm = llm.with_structured_output(ReflexionAnalysisSchema)
                analysis_data = await structured_llm.ainvoke(prompt)
                analysis_dict = (
                    analysis_data.model_dump()
                    if hasattr(analysis_data, 'model_dump')
                    else analysis_data
                )
            else:
                response = await llm.ainvoke(prompt)
                raw_text = self._extract_response_text(response)
                analysis_dict = self._parse_json_response(raw_text)
            
            if not isinstance(analysis_dict, dict):
                analysis_dict = {}
            
            root_cause = str(analysis_dict.get('root_cause') or 'Unknown root cause')
            error_type = str(analysis_dict.get('error_type') or 'unknown')
            actionable_insights = analysis_dict.get('actionable_insights')
            if not isinstance(actionable_insights, list):
                actionable_insights = (
                    [str(actionable_insights)]
                    if actionable_insights not in (None, '')
                    else ['Provide structured JSON output for reflexion analysis.']
                )
            
            # 2. Armazenar na Memoria de Trabalho (Curto Prazo)
            wm = get_working_memory()
            wm.add(
                type='reflexion',
                content=f"Failure Analysis: {root_cause}. Insights: {actionable_insights}",
                metadata={
                    'error_type': error_type,
                    'cycle_id': state.get('cycle_id'),
                    'retry_count': retry_count
                }
            )
            
            # 3. Atualizar Estado
            return {
                'error_analysis': {
                    'root_cause': root_cause,
                    'error_type': error_type,
                    'actionable_insights': actionable_insights,
                },
                'status': 'retry',
                'retry_count': retry_count + 1,
                # Atualiza o diagnostico para o proximo planejamento considerar os insights
                "diagnosis": f"Previous Failure: {root_cause}. Fix: {actionable_insights}",
            }
        except Exception as e:
            logger.error("log_error", message=f"Reflexion failed: {e}")
            # Se a reflexão falhar, apenas incrementa retry e tenta novamente (ou desiste)
            return {
                "status": "retry", 
                "retry_count": retry_count + 1,
                "execution_error": f"{error_msg} | Reflexion failed: {e}"
            }

    # --- Helpers ---

    def _get_execution_system(self) -> MultiAgentSystem:
        """Retorna (ou cria) o sistema multi-agente para execucao real das tarefas."""
        if self.executor is not None:
            return self.executor
        self.executor = MultiAgentSystem()
        return self.executor

    def _map_suggested_agent(self, suggested_agent: str | None) -> AgentRole:
        if not suggested_agent:
            return AgentRole.PROJECT_MANAGER
        key = str(suggested_agent).strip().lower()
        mapping = {
            "coder": AgentRole.CODER,
            "developer": AgentRole.CODER,
            "sysadmin": AgentRole.SYSADMIN,
            "ops": AgentRole.SYSADMIN,
            "monitor": AgentRole.RESEARCHER,
            "researcher": AgentRole.RESEARCHER,
            "tester": AgentRole.TESTER,
            "optimizer": AgentRole.OPTIMIZER,
            "documenter": AgentRole.DOCUMENTER,
            "project_manager": AgentRole.PROJECT_MANAGER,
            "manager": AgentRole.PROJECT_MANAGER,
        }
        return mapping.get(key, AgentRole.PROJECT_MANAGER)

    def _map_priority(self, priority: Any) -> TaskPriority:
        try:
            value = int(priority)
        except Exception:
            value = 2
        if value >= 4:
            return TaskPriority.CRITICAL
        if value == 3:
            return TaskPriority.HIGH
        if value == 2:
            return TaskPriority.MEDIUM
        return TaskPriority.LOW

    def _build_task_description(self, recommendation: dict, state: AgentState | None) -> str:
        title = recommendation.get("title") or "Untitled recommendation"
        description = recommendation.get("description") or ""
        category = recommendation.get("category") or "general"
        diagnosis = state.get("diagnosis") if state else ""
        issue_summary = ""
        if state:
            issues = state.get("detected_issues", [])
            if issues:
                issue_summary = json.dumps(issues[:3], ensure_ascii=False, indent=2)
        parts = [
            f"Tarefa: {title}",
            f"Categoria: {category}",
        ]
        if description:
            parts.append(f"Detalhes: {description}")
        if diagnosis:
            parts.append(f"Contexto do diagnóstico: {diagnosis}")
        if issue_summary:
            parts.append(f"Evidências: {issue_summary}")
        parts.append("Objetivo: execute a tarefa e entregue um resultado acionável.")
        return "\n".join(parts)

    async def _dispatch_task(self, recommendation: dict, state: AgentState | None = None) -> dict:
        """Executa uma tarefa baseada na recomendação usando o sistema multi-agente."""
        priority = recommendation.get("priority")
        agent_hint = recommendation.get("suggested_agent")
        title = recommendation.get("title")
        agent_role = self._map_suggested_agent(agent_hint)
        task_priority = self._map_priority(priority)

        logger.info("log_info", message=f"[MetaAgent] Dispatching Task: {title} (priority={priority}, agent={agent_hint})"
        )

        system = self._get_execution_system()
        task_description = self._build_task_description(recommendation, state)
        task = Task(description=task_description, priority=task_priority, metadata={})
        task.metadata.update(
            {
                "meta_agent_cycle": state.get("cycle_id") if state else None,
                "suggested_agent": agent_hint,
                "category": recommendation.get("category"),
            }
        )

        system.workspace.add_task(task)
        try:
            agent = await system.create_agent(agent_role)
            result = await agent.execute_task(task)
            status = result.get("status", "completed")
            return {
                "title": title,
                "status": status,
                "task_id": result.get("task_id", task.id),
                "agent_role": agent_role.value,
                "result": result.get("result") or result.get("answer"),
                "error": result.get("error"),
                "attempts": result.get("attempts"),
                "duration_seconds": result.get("duration_seconds"),
            }
        except Exception as e:
            logger.error("log_error", message=f"Erro ao executar recomendacao '{title}': {e}", exc_info=True)
            return {
                "title": title,
                "status": "failed",
                "task_id": task.id,
                "agent_role": agent_role.value,
                "error": str(e),
            }

    def _state_dict_to_report(self, state: dict) -> StateReport:
        """Converte dicionário de estado para objeto StateReport."""
        issues = []
        for i_dict in state.get("detected_issues", []):
            try:
                issues.append(
                    DetectedIssue(
                        id=i_dict.get("id", "unknown"),
                        severity=safe_issue_severity(i_dict.get("severity")),
                        category=safe_issue_category(i_dict.get("category")),
                        title=i_dict.get("title", ""),
                        description=i_dict.get("description", ""),
                        evidence=i_dict.get("evidence", {}),
                        detected_at=datetime.fromisoformat(
                            i_dict.get("detected_at", datetime.now().isoformat())
                        ),
                    )
                )
            except Exception as e:
                logger.warning("log_warning", message=f"Error converting issue to obj: {e}")

        recs = []
        for r_dict in state.get("final_plan", []):
            try:
                recs.append(
                    Recommendation(
                        id=str(uuid.uuid4()),
                        category=safe_issue_category(r_dict.get("category", "performance")),
                        title=r_dict.get("title", ""),
                        description=r_dict.get("description", ""),
                        rationale="Generated by Meta Agent",
                        estimated_impact="High",
                        priority=r_dict.get("priority", 3),
                        suggested_agent=r_dict.get("suggested_agent"),
                        created_at=datetime.now(),
                    )
                )
            except Exception as e:
                logger.warning("log_warning", message=f"Error converting recommendation to obj: {e}")

        health_score = 100 - (len(issues) * 10)
        health_score = max(0, health_score)

        META_AGENT_HEALTH_SCORE.set(health_score)

        try:
            return StateReport(
                cycle_id=state.get("cycle_id", "unknown"),
                timestamp=datetime.fromtimestamp(
                    state.get("timestamp", datetime.now().timestamp())
                ),
                overall_status=state.get("status", "unknown"),
                health_score=health_score,
                issues_detected=issues,
                recommendations=recs,
                summary=state.get("diagnosis", "No diagnosis"),
                metrics_snapshot=state.get("metrics", {}),
                execution_results=state.get("execution_results", []),
            )
        except Exception as e:
            logger.error("log_error", message=f"Error creating StateReport object: {e}")
            raise

    def _log_report(self, report: StateReport):
        logger.info("log_info", message=f"Report Generated: {report.cycle_id} | Status: {report.overall_status} | Issues: {len(report.issues_detected)}"
        )

    def _create_skipped_report(self, reason: str) -> StateReport:
        return StateReport(
            cycle_id=f"skipped_{reason}",
            timestamp=datetime.now(),
            overall_status="skipped",
            health_score=self.last_report.health_score if self.last_report else 0,
            issues_detected=self.last_report.issues_detected if self.last_report else [],
            recommendations=self.last_report.recommendations if self.last_report else [],
            summary=f"Cycle skipped due to {reason}",
            metrics_snapshot=self.last_report.metrics_snapshot if self.last_report else {},
            execution_results=self.last_report.execution_results if self.last_report else [],
        )

    def _create_error_report(self, error: str) -> StateReport:
        META_AGENT_CYCLES.labels("error").inc()
        return StateReport(
            cycle_id="error",
            timestamp=datetime.now(),
            overall_status="error",
            health_score=0,
            issues_detected=[],
            recommendations=[],
            summary=f"Cycle failed: {error}",
            metrics_snapshot={},
            execution_results=[],
        )


# Factory global
_meta_agent_instance: MetaAgent | None = None


def get_meta_agent() -> MetaAgent:
    global _meta_agent_instance
    if _meta_agent_instance is None:
        _meta_agent_instance = MetaAgent()
    return _meta_agent_instance
