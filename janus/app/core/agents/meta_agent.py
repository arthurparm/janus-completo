"""
Meta-Agente de Auto-Otimização - A Consciência Proativa do Janus (Sprint 13).

O Meta-Agente é um supervisor autônomo que monitora continuamente a saúde
e eficiência do ecossistema Janus, identificando padrões de falha e propondo
melhorias sem intervenção humana.
"""

import asyncio
import json
import logging
import uuid
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

from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm.router import ModelPriority, ModelRole, get_llm
from app.core.monitoring.health_monitor import get_health_monitor

logger = logging.getLogger(__name__)

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
        # Init LangGraph
        self.graph_builder = MetaAgentGraphBuilder(self)
        self.app = self.graph_builder.build()

        self.last_report: StateReport | None = None
        self.cycle_count = 0
        # self._initialize_agent() called lazily

    async def _initialize_agent(self):
        try:
            self.llm = await get_llm(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY
            )
            logger.info("Meta-Agente (LangGraph) inicializado com sucesso.")
        except Exception as e:
            logger.warning(f"Meta-Agente iniciou sem LLM: {e}")
            self.llm = None

    async def run_analysis_cycle(self) -> StateReport:
        """Entry point do ciclo (via LangGraph)."""
        if not self.llm:
            await self._initialize_agent()
        if not self.llm:
            return self._create_error_report("LLM Unavailable")

        cycle_id = f"cycle_{self.cycle_count}_{int(datetime.now().timestamp())}"
        self.cycle_count += 1

        # Init State (TypedDict)
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

        # Config for Persistence (Safety/Time Travel)
        config = {"configurable": {"thread_id": "meta_agent_main_thread"}}

        try:
            final_state_dict = await self.app.ainvoke(initial_state, config=config)

            # Converte Output Dict para Relatório
            report = self._state_dict_to_report(final_state_dict)
            self.last_report = report
            self._log_report(report)
            return report

        except Exception as e:
            logger.error(f"Erro fatal no LangGraph do Meta-Agente: {e}", exc_info=True)
            return self._create_error_report(str(e))

    # --- Core Logic (Adapted for Dict State) ---

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
                logger.warning(f"Error parsing metrics for heuristic check: {e}")

            return {"metrics": metrics, "detected_issues": issues}

        except Exception as e:
            logger.error(f"Error in monitor node: {e}", exc_info=True)
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
                structured_llm = self.llm.with_structured_output(DiagnosisSchema)
                diag_result = await structured_llm.ainvoke(prompt)

                if hasattr(diag_result, "root_cause"):
                    return {"diagnosis": diag_result.root_cause}
                elif isinstance(diag_result, dict):
                    return {"diagnosis": diag_result.get("root_cause", str(diag_result))}
                else:
                    return {"diagnosis": str(diag_result)}
            except Exception as parse_err:
                logger.warning(
                    f"Structured output failed for diagnosis: {parse_err}. Falling back to raw."
                )
                response = await self.llm.ainvoke(prompt)
                return {"diagnosis": response.content}
        except Exception as e:
            logger.error(f"Error in diagnosis node: {e}", exc_info=True)
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
                structured_llm = self.llm.with_structured_output(PlanSchema)
                plan_result = await structured_llm.ainvoke(prompt)

                recommendations = []
                if hasattr(plan_result, "recommendations"):
                    recommendations = [rec.dict() for rec in plan_result.recommendations]
                elif isinstance(plan_result, dict):
                    recommendations = plan_result.get("recommendations", [])

                return {"candidate_plan": recommendations}

            except Exception as parse_err:
                logger.warning(f"Structured output failed for plan: {parse_err}")
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
            logger.error(f"Error in planning node: {e}", exc_info=True)
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
                structured_llm = self.llm.with_structured_output(CritiqueSchema)
                critique_result = await structured_llm.ainvoke(prompt)

                critique_dict = (
                    critique_result.dict() if hasattr(critique_result, "dict") else critique_result
                )
                if not isinstance(critique_dict, dict):
                    critique_dict = {"approved": False, "reason": "Invalid critique structure"}

                if critique_dict.get("approved"):
                    return {"critique": critique_dict, "final_plan": plan, "status": "approved"}
                else:
                    return {
                        "critique": critique_dict,
                        "status": "retry",
                        "retry_count": state.get("retry_count", 0) + 1,
                    }
            except Exception as parse_err:
                logger.warning(f"Structured critique failed: {parse_err}")
                return {
                    "critique": {"approved": False, "reason": "Critique parsing failed"},
                    "status": "retry",
                    "retry_count": state.get("retry_count", 0) + 1,
                }
        except Exception as e:
            logger.error(f"Error in reflection node: {e}", exc_info=True)
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

        try:
            for rec in plan:
                self._dispatch_task(rec)
                results.append({"title": rec.get("title"), "status": "dispatched"})
                logger.info(f"Dispatched recommendation: {rec.get('title')}")

                META_AGENT_RECOMMENDATIONS.labels(rec.get("category", "general")).inc()

            META_AGENT_CYCLES.labels("success").inc()
            return {"execution_results": results, "status": "completed"}

        except Exception as e:
            logger.error(f"[MetaAgent] Execution Failed: {e}", exc_info=True)
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
            structured_llm = llm.with_structured_output(ReflexionAnalysisSchema)
            analysis_data = await structured_llm.ainvoke(prompt)
            
            # 2. Armazenar na Memória de Trabalho (Curto Prazo)
            wm = get_working_memory()
            wm.add(
                type="reflexion",
                content=f"Failure Analysis: {analysis_data.root_cause}. Insights: {analysis_data.actionable_insights}",
                metadata={
                    "error_type": analysis_data.error_type,
                    "cycle_id": state.get("cycle_id"),
                    "retry_count": retry_count
                }
            )

            # 3. Atualizar Estado
            return {
                "error_analysis": analysis_data.model_dump(),
                "status": "retry",
                "retry_count": retry_count + 1,
                # Atualiza o diagnóstico para o próximo planejamento considerar os insights
                "diagnosis": f"Previous Failure: {analysis_data.root_cause}. Fix: {analysis_data.actionable_insights}", 
            }

        except Exception as e:
            logger.error(f"Reflexion failed: {e}")
            # Se a reflexão falhar, apenas incrementa retry e tenta novamente (ou desiste)
            return {
                "status": "retry", 
                "retry_count": retry_count + 1,
                "execution_error": f"{error_msg} | Reflexion failed: {e}"
            }

    # --- Helpers ---

    def _dispatch_task(self, recommendation: dict):
        """Despacha uma tarefa baseada na recomendação."""
        logger.info(
            f"[MetaAgent] Dispatching Task: {recommendation.get('title')}",
            priority=recommendation.get("priority"),
            agent=recommendation.get("suggested_agent"),
        )

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
                logger.warning(f"Error converting issue to obj: {e}")

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
                logger.warning(f"Error converting recommendation to obj: {e}")

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
            )
        except Exception as e:
            logger.error(f"Error creating StateReport object: {e}")
            raise

    def _log_report(self, report: StateReport):
        logger.info(
            f"Report Generated: {report.cycle_id} | Status: {report.overall_status} | Issues: {len(report.issues_detected)}"
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
        )


# Factory global
_meta_agent_instance: MetaAgent | None = None


def get_meta_agent() -> MetaAgent:
    global _meta_agent_instance
    if _meta_agent_instance is None:
        _meta_agent_instance = MetaAgent()
    return _meta_agent_instance
