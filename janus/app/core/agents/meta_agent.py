"""
Meta-Agente de Auto-Otimização - A Consciência Proativa do Janus (Sprint 13).

O Meta-Agente é um supervisor autônomo que monitora continuamente a saúde
e eficiência do ecossistema Janus, identificando padrões de falha e propondo
melhorias sem intervenção humana.
"""
import asyncio
import logging
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import operator
from typing import TypedDict, Annotated, Literal, Union, Dict, List, Optional, Any
from typing_extensions import Required

from prometheus_client import Counter, Gauge, Histogram
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.llm.llm_manager import get_llm, ModelRole, ModelPriority
from app.core.monitoring.health_monitor import get_health_monitor

logger = logging.getLogger(__name__)

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
    suggested_agent: Optional[str] = None
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
            "suggested_agent": self.suggested_agent,
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


# --- LangGraph State Schema (Industry Benchmark) ---
class AgentState(TypedDict, total=False):
    """Estado do Agente gerenciado pelo LangGraph (TypedDict Standard)."""
    cycle_id: Required[str]
    timestamp: float
    # Metrics & Diagnosis
    metrics: Dict[str, Any]
    detected_issues: List[Dict[str, Any]] # Serialized DetectedIssue
    diagnosis: str
    
    # Planning & Reflexion
    candidate_plan: List[Dict[str, Any]] # Serialized Recommendation
    critique: Optional[Dict[str, Any]]
    final_plan: List[Dict[str, Any]]
    
    # Execution
    execution_results: List[Dict[str, Any]]
    
    # Control Flow
    status: str
    retry_count: int
    max_retries: int
    
    # History (if needed for chat)
    # messages: Annotated[List[BaseMessage], operator.add]

# --- Helper to serialize dataclasses to dict for LangGraph state ---
def _serialize_issue(issue: DetectedIssue) -> Dict[str, Any]:
    return issue.to_dict()

def _serialize_recommendation(rec: Recommendation) -> Dict[str, Any]:
    return rec.to_dict()


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
    Analisa tendências de performance de uma métrica específica baseada em dados em memória.
    
    Args:
        metric_name: Nome da métrica (ex: llm_latency, task_duration, component_health)
        hours: Janela de tempo para análise
    
    Returns:
        JSON string com análise de tendências
    """
    import json
    import statistics
    from app.core.monitoring.health_monitor import _latency_windows, HealthMonitor, get_health_monitor
    
    try:
        data_points = []
        
        # 1. Tentar obter dados de latência do HealthMonitor
        if "latency" in metric_name:
            # Tentar inferir o componente pelo nome da métrica ou usar todos
            component = None
            if "_" in metric_name:
                 parts = metric_name.split("_")
                 if parts[0] in _latency_windows:
                     component = parts[0]
            
            if component:
                 vals = list(_latency_windows.get(component, []))
                 data_points = vals
            else:
                # Agrega latências de todos os componentes se não especificado
                all_vals = []
                for q in _latency_windows.values():
                    all_vals.extend(list(q))
                data_points = all_vals

        # 2. Se for health score
        elif "health" in metric_name:
             monitor = get_health_monitor()
             # Health monitor armazena apenas último estado, então retornamos snapshot atual
             # Idealmente teríamos histórico, mas por enquanto usamos estado atual
             score = monitor.get_system_health().get("score", 0)
             data_points = [score]

        if not data_points:
             return json.dumps({
                "metric": metric_name,
                "status": "no_data",
                "message": f"Sem dados históricos para a métrica '{metric_name}' na memória."
            })
            
        # Calcular estatísticas básicas
        avg = statistics.mean(data_points) if data_points else 0
        p95 = statistics.quantiles(data_points, n=20)[-1] if len(data_points) >= 20 else max(data_points) if data_points else 0
        
        # Simples detecção de tendência (comparar primeira e segunda metade)
        trend = "stable"
        if len(data_points) > 10:
            mid = len(data_points) // 2
            first_half = statistics.mean(data_points[:mid])
            second_half = statistics.mean(data_points[mid:])
            if second_half > first_half * 1.1:
                trend = "degrading" # Aumento de latência/valor
            elif second_half < first_half * 0.9:
                trend = "improving"

        analysis = {
            "metric": metric_name,
            "data_points_count": len(data_points),
            "trend": trend,
            "average": round(avg, 4),
            "p95": round(p95, 4),
            "min": round(min(data_points), 4) if data_points else 0,
            "max": round(max(data_points), 4) if data_points else 0
        }

        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Erro ao analisar performance: {e}")
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_resource_usage() -> str:
    """
    Obtém informações detalhadas sobre uso de recursos do sistema via psutil.
    
    Returns:
        JSON string com uso de CPU, memória, disco e rede.
    """
    try:
        import psutil
        import os

        # Processo atual
        process = psutil.Process(os.getpid())
        
        resources = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent_total": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else "N/A"
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "percent_used": psutil.virtual_memory().percent,
                "swap_used_percent": psutil.swap_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024 ** 3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024 ** 3), 2),
                "percent_used": psutil.disk_usage('/').percent
            },
            "process": {
                "cpu_percent": process.cpu_percent(interval=None),
                "memory_info_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "threads": process.num_threads()
            }
        }

        return json.dumps(resources, indent=2)

    except ImportError:
         return json.dumps({"status": "error", "message": "Biblioteca 'psutil' não instalada."})
    except Exception as e:
        logger.error(f"Erro ao obter recursos: {e}", exc_info=True)
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
    {{
      "category": "categoria",
      "title": "Título da recomendação",
      "description": "O que fazer",
      "rationale": "Por que fazer",
      "priority": 1-5,
      "suggested_agent": "sysadmin|coder|researcher|optimizer"
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

# --- Retry Logic ---
import tenacity
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded

# Helper for robust invoking
class MetaAgentRetryStrategy:
    @staticmethod
    def is_retryable_error(exception):
        return isinstance(exception, (ServiceUnavailable, DeadlineExceeded))




# --- Meta-Agente ---

# --- Meta-Agent Graph Architecture (SOTA 2025) ---

# --- Meta-Agent Graph Architecture (Official LangGraph SOTA) ---

class MetaAgentGraphBuilder:
    """Builder for the LangGraph StateGraph."""
    
    
    def __init__(self, agent_instance):
        self.agent = agent_instance
        # Use direct connection for persistence to avoid context manager ambiguity
        import sqlite3
        import os
        
        # Ensure data directory exists (using ephemeral /tmp to surpass windows volume locking)
        db_path = "/tmp/meta_agent_langgraph.db"
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)

    def build(self):
        workflow = StateGraph(AgentState)

        # 1. Add Nodes
        workflow.add_node("monitor", self._node_monitor_wrapper)
        workflow.add_node("diagnose", self._node_diagnose_wrapper)
        workflow.add_node("plan", self._node_plan_wrapper)
        workflow.add_node("reflect", self._node_reflect_wrapper)
        workflow.add_node("execute", self._node_execute_wrapper)
        workflow.add_node("dead_letter", self._node_dead_letter_wrapper)

        # 2. Add Edges
        workflow.add_edge(START, "monitor")
        
        # Monitor -> Diagnose (or End if healthy)
        workflow.add_conditional_edges(
            "monitor",
            self._check_health,
            {"healthy": END, "unhealthy": "diagnose"}
        )
        
        workflow.add_edge("diagnose", "plan")
        workflow.add_edge("plan", "reflect")
        
        # Reflexion Loop: Reflect -> Execute (Approved) OR Plan (Retry)
        workflow.add_conditional_edges(
            "reflect",
            self._check_critique,
            {
                "approved": "execute",
                "retry": "plan",
                "give_up": "dead_letter"
            }
        )
        
        workflow.add_edge("execute", END)
        workflow.add_edge("dead_letter", END)

        # 3. Compile
        return workflow.compile(checkpointer=self.checkpointer)

    # --- Node Wrappers (Adapter Pattern: TypedDict <-> Logic) ---
    
    async def _node_monitor_wrapper(self, state: AgentState) -> dict:
        # Call original method (adapted to return dict updates)
        return await self.agent.monitor_node_logic(state)

    async def _node_diagnose_wrapper(self, state: AgentState) -> dict:
        return await self.agent.diagnosis_node_logic(state)

    async def _node_plan_wrapper(self, state: AgentState) -> dict:
        return await self.agent.planning_node_logic(state)
        
    async def _node_reflect_wrapper(self, state: AgentState) -> dict:
        return await self.agent.reflection_node_logic(state)

    async def _node_execute_wrapper(self, state: AgentState) -> dict:
        return await self.agent.execution_node_logic(state)
        
    async def _node_dead_letter_wrapper(self, state: AgentState) -> dict:
        logger.critical(f"DEAD LETTER: Cycle {state.get('cycle_id')} failed after max retries.")
        # Alerting logic here
        return {"status": "dead_letter"}

    # --- Conditional Logic ---
    
    def _check_health(self, state: AgentState) -> Literal["healthy", "unhealthy"]:
        # If issues list is empty, it's healthy
        if not state.get("detected_issues"):
            return "healthy"
        return "unhealthy"

    def _check_critique(self, state: AgentState) -> Literal["approved", "retry", "give_up"]:
        critique = state.get("critique", {})
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if critique.get("approved"):
            return "approved"
        
        if retry_count >= max_retries:
            return "give_up"
            
        return "retry"

# --- Pydantic Schemas for Strict Validation (SOTA 2025) ---
from pydantic import BaseModel, Field, ValidationError

class DiagnosisSchema(BaseModel):
    root_cause: str = Field(..., description="A causa raiz técnica identificada.")
    severity: str = Field(..., description="Gravidade: low, medium, high, critical")
    confidence: float = Field(..., description="Nível de confiança no diagnóstico (0.0 a 1.0)")

class RecommendationItem(BaseModel):
    title: str
    description: str
    priority: int = Field(..., ge=1, le=5)
    suggested_agent: str = Field(..., pattern="^(sysadmin|coder|monitor)$")
    category: str = "performance"

class PlanSchema(BaseModel):
    recommendations: List[RecommendationItem]

class CritiqueSchema(BaseModel):
    approved: bool
    reason: str
    safe_subset_ids: List[str] = Field(default_factory=list)

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
            get_resource_usage
        ]
        self.llm = None
        # Init LangGraph
        self.graph_builder = MetaAgentGraphBuilder(self)
        self.app = self.graph_builder.build()
        
        self.last_report: Optional[StateReport] = None
        self.cycle_count = 0
        self._initialize_agent()

    def _initialize_agent(self):
        try:
            self.llm = get_llm(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY)
            logger.info("Meta-Agente (LangGraph) inicializado com sucesso.")
        except Exception as e:
            logger.warning(f"Meta-Agente iniciou sem LLM: {e}")
            self.llm = None

    async def run_analysis_cycle(self) -> StateReport:
        """Entry point do ciclo (via LangGraph)."""
        if not self.llm: self._initialize_agent()
        if not self.llm: return self._create_error_report("LLM Unavailable")

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
            "max_retries": 3
        }
        
        # Config for Persistence (Safety/Time Travel)
        config = {"configurable": {"thread_id": "meta_agent_main_thread"}}
        
        try:
            # Run Graph
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
        # Coleta paralela
        results = await asyncio.gather(
            asyncio.to_thread(get_system_health_metrics.invoke, {}),
            asyncio.to_thread(analyze_memory_for_failures.invoke, {"time_window_hours": 24, "max_results": 20}),
            asyncio.to_thread(get_resource_usage.invoke, {})
        )
        
        metrics = {
            "health": results[0],
            "failures": results[1],
            "resources": results[2]
        }
        
        issues = []
        if '"status": "unhealthy"' in str(metrics):
             issues.append(DetectedIssue(id="unhealthy_sys", severity=IssueSeverity.HIGH, category=IssueCategory.RELIABILITY, title="Sistema Unhealthy", description="Health check retornou status unhealthy", evidence={}).to_dict())
        
        try:
            fails = json.loads(results[1]) if isinstance(results[1], str) else {}
            if fails.get("status") == "failures_found":
                 issues.append(DetectedIssue(id="mem_failures", severity=IssueSeverity.MEDIUM, category=IssueCategory.RELIABILITY, title="Falhas Recentes Detectadas", description=f"{fails.get('total_failures')} falhas encontradas na memória", evidence=fails).to_dict())
        except: pass

        # Return Partial Update
        return {
            "metrics": metrics,
            "detected_issues": issues,
            "status": "monitoring"
        }



# --- MetaAgent Class Updates ---

# --- Logic Nodes (Continued) ---

    async def diagnosis_node_logic(self, state: AgentState) -> dict:
        """Usa LLM para analisar a causa raiz (Validado por Pydantic)."""
        logger.info("[MetaAgent] Node: Diagnosis")
        metrics = state.get("metrics", {})
        
        prompt = (
            f"Analise estas métricas do sistema Janus e diagnostique a causa raiz:\n"
            f"{json.dumps(metrics, indent=2)}\n\n"
            f"Saída OBRIGATÓRIA em JSON compatível com este Schema:\n{json.dumps(DiagnosisSchema.model_json_schema(), indent=2)}"
        )
        response = await self._invoke_llm(prompt, timeout=120)
        
        diagnosis_str = ""
        new_issues = []
        
        try:
            clean_json = self._extract_json(response)
            diagnosis_obj = DiagnosisSchema.model_validate_json(clean_json)
            diagnosis_str = f"[{diagnosis_obj.severity.upper()}] {diagnosis_obj.root_cause} (Conf: {diagnosis_obj.confidence})"
            
            if diagnosis_obj.severity == "critical":
                new_issues.append(DetectedIssue(id="diag_crit", severity=IssueSeverity.CRITICAL, category=IssueCategory.RELIABILITY, title=diagnosis_obj.root_cause, description="Diagnosed Critical Issue", evidence={"confidence": diagnosis_obj.confidence}).to_dict())
                
        except ValidationError as e:
            logger.error(f"Diagnosis Validation Failed: {e}")
            diagnosis_str = "Diagnosis Failed (Schema Error)"
        except Exception as e:
            logger.warning(f"Diagnosis Error: {e}")
            diagnosis_str = "Diagnosis Failed (Unknown)"
            
        current_issues = state.get("detected_issues", [])
        return {
            "diagnosis": diagnosis_str,
            "detected_issues": current_issues + new_issues,
            "status": "diagnosing"
        }

    async def planning_node_logic(self, state: AgentState) -> dict:
        """Gera recomendações de correção (Validado por Pydantic)."""
        retry_count = state.get("retry_count", 0)
        logger.info(f"[MetaAgent] Node: Planning (Attempt {retry_count + 1})")
        
        critique_context = ""
        critique = state.get("critique")
        if retry_count > 0 and critique:
            critique_context = (
                f"\n\n[ATENÇÃO] O plano anterior foi REJEITADO.\n"
                f"Motivo: {critique.get('reason')}\n"
                "Gere um NOVO plano corrigido."
            )

        prompt = (
            f"Diagnóstico: {state.get('diagnosis')}{critique_context}\n"
            "Gere Recomendações Técnicas.\n"
            f"Saída OBRIGATÓRIA em JSON compatível com este Schema:\n{json.dumps(PlanSchema.model_json_schema(), indent=2)}"
        )
        response = await self._invoke_llm(prompt, timeout=120)
        candidate_plan = []
        
        try:
            clean_json = self._extract_json(response)
            plan_obj = PlanSchema.model_validate_json(clean_json)
            
            candidate_plan = [
                Recommendation(
                    id=str(uuid.uuid4()), 
                    category=_safe_issue_category(item.category),
                    title=item.title,
                    description=item.description,
                    priority=item.priority,
                    suggested_agent=item.suggested_agent
                ).to_dict() for item in plan_obj.recommendations
            ]
        except Exception as e:
            logger.error(f"Planning Failed: {e}")
        
        return {
            "candidate_plan": candidate_plan,
            "status": "planning"
        }

    async def reflection_node_logic(self, state: AgentState) -> dict:
        """Critica o plano (Auto-Reflexão)."""
        logger.info("[MetaAgent] Node: Reflection (Crisis Committee)")
        
        plan = state.get("candidate_plan", [])
        diagnosis = state.get("diagnosis", "")
        
        if not plan:
            return {"critique": {"approved": False, "reason": "Empty Plan generated"}, "retry_count": state.get("retry_count", 0) + 1}

        prompt = (
             f"DIAGNÓSTICO: {diagnosis}\n"
             f"PLANO PROPOSTO: {json.dumps(plan, indent=2)}\n\n"
             "Você aprova este plano? É seguro e resolve o problema?\n"
             f"Saída OBRIGATÓRIA em JSON compatível com este Schema:\n{json.dumps(CritiqueSchema.model_json_schema(), indent=2)}"
        )
        response = await self._invoke_llm(prompt, timeout=60, role_override=ModelRole.CRITIC)
        
        critique_dict = {"approved": False, "reason": "Validation Failed"}
        try:
            clean_json = self._extract_json(response)
            critique_obj = CritiqueSchema.model_validate_json(clean_json)
            critique_dict = critique_obj.model_dump()
        except Exception as e:
            logger.error(f"Critique Failed: {e}")
        
        # Calculate increments
        retry_inc = 0
        if not critique_dict["approved"]:
             retry_inc = 1
             
        return {
            "critique": critique_dict,
            "retry_count": state.get("retry_count", 0) + retry_inc,
            "status": "reflecting"
        }

    async def execution_node_logic(self, state: AgentState) -> dict:
        """Simula execução ou delega para agentes."""
        logger.info("[MetaAgent] Node: Execution")
        # Por enquanto, apenas consolidamos o plano como 'Final'
        return {
            "final_plan": state.get("candidate_plan"),
            "status": "executed"
        }

    # --- Helpers ---

    def _state_dict_to_report(self, state_dict: dict) -> StateReport:
        items = state_dict.get("detected_issues", [])
        # Rehydrate objects
        issues = [DetectedIssue(**i) if isinstance(i, dict) else i for i in items] # Simplification
        
        # Fix DetectedIssue rehydration properly if needed
        # For now assuming simple strict casting isn't needed for display only, or we fix constructor
        
        # Actually issues are dicts in the state now. DetectedIssue(**dict) should work if keys match.
        # But wait, `DetectedIssue` uses Enums. We serialized them to values.
        # We need to deserialize properly.
        
        real_issues = []
        for i in items:
            try:
                # Handle enum conversion
                i_copy = i.copy()
                i_copy["severity"] = _safe_issue_severity(i.get("severity"))
                i_copy["category"] = _safe_issue_category(i.get("category"))
                if "detected_at" in i_copy and isinstance(i_copy["detected_at"], str):
                     i_copy["detected_at"] = datetime.fromisoformat(i_copy["detected_at"])
                real_issues.append(DetectedIssue(**i_copy))
            except: pass

        recs = []
        for r in state_dict.get("final_plan", []):
            try:
                 r_copy = r.copy()
                 r_copy["category"] = _safe_issue_category(r.get("category"))
                 if "created_at" in r_copy and isinstance(r_copy["created_at"], str):
                     r_copy["created_at"] = datetime.fromisoformat(r_copy["created_at"])
                 recs.append(Recommendation(**r_copy))
            except: pass

        return StateReport(
            cycle_id=state_dict.get("cycle_id"),
            timestamp=datetime.fromtimestamp(state_dict.get("timestamp", 0)),
            overall_status=state_dict.get("status", "unknown"),
            health_score=80, # Placeholder
            issues_detected=real_issues,
            recommendations=recs,
            summary=state_dict.get("diagnosis", ""),
            metrics_snapshot=state_dict.get("metrics", {})
        )

    def _create_error_report(self, error_msg: str) -> StateReport:
        return StateReport(
            cycle_id="error",
            timestamp=datetime.now(),
            overall_status="critical",
            health_score=0,
            issues_detected=[DetectedIssue(id="fatal", severity=IssueSeverity.CRITICAL, category=IssueCategory.RELIABILITY, title="Fatal Error", description=error_msg, evidence={})],
            recommendations=[],
            summary=f"Agent Failure: {error_msg}",
            metrics_snapshot={}
        )

    async def _invoke_llm(self, prompt: str, timeout: int = 60, role_override=None):
        # ... logic unchanged ...
        return await self.llm.ainvoke(prompt) # Simplified

    def _extract_json(self, text):
        # ... helper ...
        if hasattr(text, "content"): text = text.content
        import re
        match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
        return match.group(0) if match else "{}"
    




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

    async def _auto_remediate(self, report: StateReport):
        """Tenta remediar automaticamente problemas críticos criando tarefas para agentes."""
        if not report.recommendations:
            return

        from app.core.agents.multi_agent_system import get_multi_agent_system, Task, TaskPriority, TaskStatus

        mas = get_multi_agent_system()
        
        for rec in report.recommendations:
            # Apenas cria tarefas para prioridade alta/crítica e com agente sugerido
            if rec.priority >= 4 and rec.suggested_agent:
                target_agent_id = None
                
                # Tenta mapear o agente sugerido para um ID real
                # Pega lista de agentes ativos
                for agent_id, agent in mas.agents.items():
                    if agent.role.value == rec.suggested_agent.lower():
                        target_agent_id = agent_id
                        break
                
                if target_agent_id:
                    logger.info(f"Meta-Agente: Criando tarefa de remediação para {target_agent_id}")
                    
                    task = Task(
                        description=f"[AUTO-REMEDIATION] {rec.title}: {rec.description}",
                        assigned_to=target_agent_id,
                        priority=TaskPriority.CRITICAL if rec.priority == 5 else TaskPriority.HIGH,
                        metadata={
                            "source": "meta_agent",
                            "recommendation_id": rec.id,
                            "rationale": rec.rationale
                        }
                    )
                    
                    mas.workspace.add_task(task)
                    await mas.dispatch_task(task)
                else:
                    logger.warning(f"Meta-Agente: Agente sugerido '{rec.suggested_agent}' não encontrado para aplicar correção.")

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
