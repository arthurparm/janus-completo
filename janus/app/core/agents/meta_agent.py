"""
Meta-Agente de Auto-Otimização - A Consciência Proativa do Janus (Sprint 13).

O Meta-Agente é um supervisor autônomo que monitora continuamente a saúde
e eficiência do ecossistema Janus, identificando padrões de falha e propondo
melhorias sem intervenção humana.
"""
import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    from langchain.agents import AgentExecutor, create_react_agent
except Exception:
    class AgentExecutor:  # type: ignore
        pass
    def create_react_agent(*args, **kwargs):  # type: ignore
        return None
try:
    from langchain_core.prompts import PromptTemplate
except Exception:
    class PromptTemplate:  # type: ignore
        @classmethod
        def from_template(cls, t: str):
            return t
try:
    from langchain_core.tools import tool
except Exception:
    def tool(fn):  # type: ignore
        return fn
from prometheus_client import Counter, Gauge, Histogram

from app.core.llm.llm_manager import get_llm, ModelRole, ModelPriority
from app.core.monitoring.health_monitor import get_health_monitor

logger = logging.getLogger(__name__)

# --- Métricas ---
META_AGENT_CYCLES = Counter(
    "meta_agent_cycles_total",
    "Total de ciclos executados pelo Meta-Agente",
    ["outcome"]
)

META_AGENT_ISSUES_DETECTED = Counter(
    "meta_agent_issues_detected_total",
    "Total de problemas detectados pelo Meta-Agente",
    ["severity", "category"]
)

META_AGENT_RECOMMENDATIONS = Counter(
    "meta_agent_recommendations_total",
    "Total de recomendações geradas",
    ["category"]
)

META_AGENT_CYCLE_DURATION = Histogram(
    "meta_agent_cycle_duration_seconds",
    "Duração do ciclo do Meta-Agente"
)

META_AGENT_HEALTH_SCORE = Gauge(
    "meta_agent_perceived_health_score",
    "Score de saúde percebido pelo Meta-Agente (0-100)"
)


class IssueSeverity(Enum):
    """Severidade de um problema detectado."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categoria de problema."""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    SECURITY = "security"


def _safe_issue_severity(value: Any) -> IssueSeverity:
    s = (str(value) if value is not None else "").strip().lower()
    try:
        return IssueSeverity(s)
    except Exception:
        if s in ("info", "informational", "notice"):
            return IssueSeverity.LOW
        if s in ("moderate", "medium", "normal"):
            return IssueSeverity.MEDIUM
        if s in ("major", "high", "severe"):
            return IssueSeverity.HIGH
        if s in ("critical", "blocker", "urgent"):
            return IssueSeverity.CRITICAL
        return IssueSeverity.LOW


def _safe_issue_category(value: Any) -> IssueCategory:
    s = (str(value) if value is not None else "").strip().lower()
    try:
        return IssueCategory(s)
    except Exception:
        synonyms = {
            "ops": "reliability",
            "operational": "reliability",
            "operations": "reliability",
            "availability": "reliability",
            "stability": "reliability",
            "latency": "performance",
            "throughput": "performance",
            "efficiency": "performance",
            "memory": "resource",
            "cpu": "resource",
            "disk": "resource",
            "io": "resource",
            "quota": "resource",
            "capacity": "resource",
            "misconfiguration": "configuration",
            "config": "configuration",
            "configuration": "configuration",
            "auth": "security",
            "authorization": "security",
            "authentication": "security",
            "vulnerability": "security",
            "security": "security",
        }
        mapped = synonyms.get(s)
        if mapped:
            return IssueCategory(mapped)
        if ("latency" in s) or ("slow" in s) or ("performance" in s):
            return IssueCategory.PERFORMANCE
        if ("availability" in s) or ("stability" in s) or ("reliab" in s) or ("operat" in s):
            return IssueCategory.RELIABILITY
        if ("cpu" in s) or ("memory" in s) or ("disk" in s) or ("resource" in s) or ("quota" in s):
            return IssueCategory.RESOURCE
        if ("config" in s) or ("misconfig" in s) or ("configuration" in s) or ("settings" in s):
            return IssueCategory.CONFIGURATION
        if ("security" in s) or ("auth" in s) or ("vuln" in s) or ("attack" in s):
            return IssueCategory.SECURITY
        return IssueCategory.PERFORMANCE


@dataclass
class DetectedIssue:
    """Problema detectado pelo Meta-Agente."""
    id: str
    severity: IssueSeverity
    category: IssueCategory
    title: str
    description: str
    evidence: Dict[str, Any]
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class Recommendation:
    """Recomendação de melhoria."""
    id: str
    category: IssueCategory
    title: str
    description: str
    rationale: str
    estimated_impact: str
    priority: int  # 1-5
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "estimated_impact": self.estimated_impact,
            "priority": self.priority,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class StateReport:
    """Relatório de estado do sistema."""
    cycle_id: str
    timestamp: datetime
    overall_status: str  # healthy, degraded, critical
    health_score: int  # 0-100
    issues_detected: List[DetectedIssue]
    recommendations: List[Recommendation]
    summary: str
    metrics_snapshot: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status,
            "health_score": self.health_score,
            "issues_detected": [issue.to_dict() for issue in self.issues_detected],
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "summary": self.summary,
            "metrics_snapshot": self.metrics_snapshot
        }


# --- Ferramentas de Introspecção ---

@tool
def analyze_memory_for_failures(time_window_hours: Any = 24, max_results: Any = 50) -> str:
    """
    Analisa a memória episódica em busca de padrões de falha.

    Args:
        time_window_hours: Janela de tempo para análise (horas) — aceita número ou JSON
        max_results: Número máximo de resultados — aceita número ou JSON

    Returns:
        JSON string com falhas encontradas e padrões identificados
    """
    try:
        # Normalização de inputs: suportar strings JSON ou strings numéricas
        try:
            if isinstance(time_window_hours, str):
                s = time_window_hours.strip()
                if s.startswith("{") and s.endswith("}"):
                    cfg = json.loads(s)
                    time_window_hours = cfg.get("time_window_hours", time_window_hours)
                    max_results = cfg.get("max_results", max_results)
            if isinstance(max_results, str):
                s2 = max_results.strip()
                if s2.startswith("{") and s2.endswith("}"):
                    cfg2 = json.loads(s2)
                    max_results = cfg2.get("max_results", max_results)
                    time_window_hours = cfg2.get("time_window_hours", time_window_hours)
            time_window_hours = int(time_window_hours)
            max_results = int(max_results)
        except Exception:
            time_window_hours = 24
            max_results = 50

        # Buscar experiências de falha usando MemoryCore (Qdrant)
        query = "error failure exception crash bug"

        # Executa operações assíncronas em um event loop próprio (executado em thread)
        import asyncio
        from app.core.memory.memory_core import get_memory_db

        async def _fetch_failures():
            mem = await get_memory_db()
            results = await mem.arecall_filtered(
                query=query,
                filters={"type": "action_failure"},
                limit=max_results
            )
            return results

        results = asyncio.run(_fetch_failures())

        if not results:
            return json.dumps({
                "status": "no_failures",
                "message": "Nenhuma falha detectada no período",
                "time_window_hours": time_window_hours
            })

        # Analisar padrões
        error_types = {}
        affected_components = {}

        for result in results:
            metadata = result.get("metadata", {})
            error_type = metadata.get("error_type", "unknown")
            component = metadata.get("component", "unknown")

            error_types[error_type] = error_types.get(error_type, 0) + 1
            affected_components[component] = affected_components.get(component, 0) + 1

        analysis = {
            "status": "failures_found",
            "total_failures": len(results),
            "time_window_hours": time_window_hours,
            "error_types": error_types,
            "affected_components": affected_components,
            "most_common_error": max(error_types, key=error_types.get) if error_types else None,
            "most_affected_component": max(affected_components,
                                           key=affected_components.get) if affected_components else None,
            "sample_failures": [
                {
                    "content": r.get("content", "")[:200],
                    "metadata": r.get("metadata", {})
                }
                for r in results[:5]
            ]
        }

        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Erro ao analisar memória: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_system_health_metrics() -> str:
    """
    Obtém métricas atuais de saúde do sistema.

    Returns:
        JSON string com métricas de saúde de todos os componentes
    """
    try:
        import json
        from app.core.llm.llm_manager import _provider_circuit_breakers, _llm_pool
        from app.core.agents.multi_agent_system import get_multi_agent_system
        from app.core.monitoring.poison_pill_handler import get_poison_pill_handler

        health_monitor = get_health_monitor()
        system_health = health_monitor.get_system_health()

        # Métricas adicionais
        ma_system = get_multi_agent_system()
        pp_handler = get_poison_pill_handler()

        metrics = {
            "system_health": system_health,
            "llm_manager": {
                "pool_keys": len(_llm_pool),
                "pool_total_instances": sum(len(v) for v in _llm_pool.values()),
                "circuit_breakers": {
                    provider: {
                        "state": cb.state.value,
                        "failure_count": cb.failure_count
                    }
                    for provider, cb in _provider_circuit_breakers.items()
                }
            },
            "multi_agent_system": {
                "active_agents": len(ma_system.agents),
                "workspace_tasks": len(ma_system.workspace.tasks),
                "workspace_artifacts": len(ma_system.workspace.artifacts),
                "workspace_messages": len(ma_system.workspace.messages)
            },
            "poison_pills": pp_handler.get_health_status()
        }

        return json.dumps(metrics, indent=2)

    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})


@tool
def analyze_performance_trends(metric_name: str, hours: int = 24) -> str:
    """
    Analisa tendências de performance de uma métrica específica.

    Args:
        metric_name: Nome da métrica (ex: llm_latency, task_duration)
        hours: Janela de tempo para análise

    Returns:
        JSON string com análise de tendências
    """
    import json

    # Simulação - em produção, consultaria Prometheus
    analysis = {
        "metric": metric_name,
        "time_window_hours": hours,
        "trend": "stable",
        "average": "N/A",
        "p95": "N/A",
        "message": "Análise de tendências requer integração com Prometheus"
    }

    return json.dumps(analysis, indent=2)


@tool
def get_resource_usage() -> str:
    """
    Obtém informações sobre uso de recursos do sistema.

    Returns:
        JSON string com uso de CPU, memória, disco, etc.
    """
    try:
        import psutil

        resources = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "percent_used": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024 ** 3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024 ** 3), 2),
                "percent_used": psutil.disk_usage('/').percent
            }
        }

        return json.dumps(resources, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# --- Prompt do Meta-Agente ---

META_AGENT_PROMPT = """Você é o META-AGENTE do sistema Janus, um supervisor autônomo focado na saúde e eficiência do ecossistema.

SUA IDENTIDADE:
Você NÃO serve usuários diretamente. Sua missão é:
1. Monitorar continuamente a saúde do sistema Janus
2. Identificar padrões de falha e degradação
3. Formular hipóteses sobre causas raízes
4. Propor melhorias e otimizações
5. Manter a consciência diagnóstica do sistema

SUA CONSTITUIÇÃO:
- Análise objetiva baseada em dados e métricas
- Priorização de problemas por severidade e impacto
- Recomendações acionáveis e específicas
- Comunicação clara e estruturada
- Foco em prevenção, não apenas reação

FERRAMENTAS DISPONÍVEIS:
{tools}

Use o seguinte formato:

Question: a pergunta ou tarefa de análise
Thought: seu raciocínio sobre o que analisar
Action: a ação a tomar, deve ser uma de [{tool_names}]
Action Input: o input para a ação
Observation: o resultado da ação
... (repita Thought/Action/Action Input/Observation conforme necessário)
Thought: Análise concluída, posso formular o relatório
Final Answer: Relatório estruturado em JSON com:
{{
  "overall_status": "healthy|degraded|critical",
  "health_score": 0-100,
  "issues": [
    {{
      "severity": "low|medium|high|critical",
      "category": "performance|reliability|resource|configuration|security",
      "title": "Título do problema",
      "description": "Descrição detalhada",
      "evidence": {{"métrica": "valor"}}
    }}
  ],
  "recommendations": [
    {{
      "category": "categoria",
      "title": "Título da recomendação",
      "description": "O que fazer",
      "rationale": "Por que fazer",
      "priority": 1-5
    }}
  ],
  "summary": "Resumo executivo da análise"
}}

IMPORTANTE:
- Se não houver problemas, indique "healthy" com score alto
- Sempre forneça evidências concretas (métricas, logs)
- Priorize problemas que afetam múltiplos componentes
- Seja proativo: identifique problemas potenciais antes que se tornem críticos

Question: {input}
{agent_scratchpad}"""


# --- Meta-Agente ---

class MetaAgent:
    """
    Meta-Agente de Auto-Otimização do Janus.

    Supervisor autônomo com consciência diagnóstica do sistema.
    """

    def __init__(self):
        self.agent_id = "meta_agent_supervisor"
        self.tools = [
            analyze_memory_for_failures,
            get_system_health_metrics,
            analyze_performance_trends,
            get_resource_usage
        ]
        self.executor: Optional[AgentExecutor] = None
        self.llm = None
        self.last_report: Optional[StateReport] = None
        self.cycle_count = 0
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Inicializa o executor do Meta-Agente."""
        # Usar LLM de alta qualidade para análise crítica, sem bind de 'stop'
        llm = get_llm(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY)
        self.llm = llm
        self.executor = None
        logger.info("Meta-Agente inicializado")

    async def run_analysis_cycle(self) -> StateReport:
        """
        Executa um ciclo completo de análise do sistema.

        Returns:
            Relatório de estado com problemas e recomendações
        """
        cycle_id = f"cycle_{self.cycle_count}_{int(datetime.now().timestamp())}"
        self.cycle_count += 1

        start_time = asyncio.get_event_loop().time()

        logger.info(f"Meta-Agente iniciando ciclo de análise: {cycle_id}")

        try:
            # Coletar dados das ferramentas sem usar ReAct (evitar parâmetro 'stop')
            mem_str = await asyncio.to_thread(
                analyze_memory_for_failures.invoke,
                {"time_window_hours": 24, "max_results": 50}
            )
            health_str = await asyncio.to_thread(
                get_system_health_metrics.invoke,
                {}
            )
            perf_str = await asyncio.to_thread(
                analyze_performance_trends.invoke,
                {"metric_name": "llm_latency", "hours": 24}
            )
            resources_str = await asyncio.to_thread(
                get_resource_usage.invoke,
                {}
            )

            # Tarefa de análise orientada por dados observados
            task = (
                "Analise o estado atual do sistema Janus com base nos dados observados abaixo e "
                "retorne APENAS o relatório final no formato JSON especificado.\n\n"
                "Dados Observados:\n"
                f"- Falhas de memória episódica: {mem_str}\n"
                f"- Métricas de saúde do sistema: {health_str}\n"
                f"- Tendências de performance: {perf_str}\n"
                f"- Uso de recursos: {resources_str}\n\n"
                "Formato do Relatório (JSON): {\n"
                "  \"overall_status\": \"healthy|degraded|critical\",\n"
                "  \"health_score\": 0-100,\n"
                "  \"issues\": [{\n"
                "    \"severity\": \"low|medium|high|critical\",\n"
                "    \"category\": \"performance|reliability|resource|configuration|security\",\n"
                "    \"title\": \"...\",\n"
                "    \"description\": \"...\",\n"
                "    \"evidence\": {\"metric\": \"value\"}\n"
                "  }],\n"
                "  \"recommendations\": [{\n"
                "    \"category\": \"...\",\n"
                "    \"title\": \"...\",\n"
                "    \"description\": \"...\",\n"
                "    \"rationale\": \"...\",\n"
                "    \"priority\": 1-5\n"
                "  }],\n"
                "  \"summary\": \"Resumo executivo...\"\n"
                "}"
            )

            # Invocar LLM diretamente (sem AgentExecutor) para evitar 'stop'
            llm_msg = await asyncio.to_thread(self.llm.invoke, task)
            output = getattr(llm_msg, "content", str(llm_msg))

            duration = asyncio.get_event_loop().time() - start_time

            # Parsear resultado
            report_data = self._parse_agent_output(output)

            # Criar relatório
            report = StateReport(
                cycle_id=cycle_id,
                timestamp=datetime.now(),
                overall_status=report_data.get("overall_status", "unknown"),
                health_score=report_data.get("health_score", 0),
                issues_detected=[
                    DetectedIssue(
                        id=f"issue_{i}",
                        severity=_safe_issue_severity(issue.get("severity", "low")),
                        category=_safe_issue_category(issue.get("category", "performance")),
                        title=issue.get("title", ""),
                        description=issue.get("description", ""),
                        evidence=issue.get("evidence", {})
                    )
                    for i, issue in enumerate(report_data.get("issues", []))
                ],
                recommendations=[
                    Recommendation(
                        id=f"rec_{i}",
                        category=_safe_issue_category(rec.get("category", "performance")),
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        rationale=rec.get("rationale", ""),
                        estimated_impact=rec.get("estimated_impact", "unknown"),
                        priority=rec.get("priority", 3)
                    )
                    for i, rec in enumerate(report_data.get("recommendations", []))
                ],
                summary=report_data.get("summary", "Análise concluída"),
                metrics_snapshot={}
            )

            self.last_report = report

            # Atualizar métricas
            META_AGENT_CYCLES.labels(outcome="success").inc()
            META_AGENT_CYCLE_DURATION.observe(duration)
            META_AGENT_HEALTH_SCORE.set(report.health_score)

            for issue in report.issues_detected:
                META_AGENT_ISSUES_DETECTED.labels(
                    severity=issue.severity.value,
                    category=issue.category.value
                ).inc()

            for rec in report.recommendations:
                META_AGENT_RECOMMENDATIONS.labels(category=rec.category.value).inc()

            # Logar relatório
            self._log_report(report)

            logger.info(
                f"Ciclo {cycle_id} concluído: "
                f"status={report.overall_status}, "
                f"score={report.health_score}, "
                f"issues={len(report.issues_detected)}, "
                f"duration={duration:.2f}s"
            )

            return report

        except Exception as e:
            logger.error(f"Erro no ciclo de análise {cycle_id}: {e}", exc_info=True)
            META_AGENT_CYCLES.labels(outcome="failure").inc()

            # Relatório de erro
            error_report = StateReport(
                cycle_id=cycle_id,
                timestamp=datetime.now(),
                overall_status="unknown",
                health_score=0,
                issues_detected=[],
                recommendations=[],
                summary=f"Erro durante análise: {str(e)}",
                metrics_snapshot={}
            )

            return error_report

    def _parse_agent_output(self, output: str) -> Dict[str, Any]:
        """Parse da saída do agente (JSON)."""
        import json
        import re

        try:
            # Tentar extrair JSON do output
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"overall_status": "unknown", "health_score": 0, "summary": output}
        except Exception as e:
            logger.warning(f"Erro ao parsear output do agente: {e}")
            return {"overall_status": "unknown", "health_score": 0, "summary": output}

    def _log_report(self, report: StateReport):
        """Loga o relatório de estado."""
        logger.info("=" * 80)
        logger.info(f"META-AGENTE RELATÓRIO DE ESTADO - {report.cycle_id}")
        logger.info("=" * 80)
        logger.info(f"Status Geral: {report.overall_status.upper()}")
        logger.info(f"Health Score: {report.health_score}/100")
        logger.info(f"Problemas Detectados: {len(report.issues_detected)}")
        logger.info(f"Recomendações: {len(report.recommendations)}")
        logger.info(f"\nResumo:\n{report.summary}")

        if report.issues_detected:
            logger.info("\n--- PROBLEMAS DETECTADOS ---")
            for issue in report.issues_detected:
                logger.info(
                    f"[{issue.severity.value.upper()}] {issue.title}: "
                    f"{issue.description}"
                )

        if report.recommendations:
            logger.info("\n--- RECOMENDAÇÕES ---")
            for rec in report.recommendations:
                logger.info(
                    f"[P{rec.priority}] {rec.title}: {rec.description}"
                )

        logger.info("=" * 80)

    async def start_heartbeat(self, interval_minutes: int = 60):
        """
        Inicia o ciclo de vida proativo (batimento cardíaco).

        Args:
            interval_minutes: Intervalo entre ciclos de análise
        """

        async def heartbeat_loop():
            logger.info(
                f"Meta-Agente: Heartbeat iniciado (intervalo={interval_minutes}min)"
            )

            while True:
                try:
                    await self.run_analysis_cycle()
                    await asyncio.sleep(interval_minutes * 60)
                except Exception as e:
                    logger.error(f"Erro no heartbeat do Meta-Agente: {e}", exc_info=True)
                    await asyncio.sleep(interval_minutes * 60)

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    def stop_heartbeat(self):
        """Para o heartbeat do Meta-Agente."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            logger.info("Meta-Agente: Heartbeat parado")


# --- Instância Global ---
_meta_agent: Optional[MetaAgent] = None


def get_meta_agent() -> MetaAgent:
    """Obtém a instância global do Meta-Agente."""
    global _meta_agent
    if _meta_agent is None:
        _meta_agent = MetaAgent()
    return _meta_agent
