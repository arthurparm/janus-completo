from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
import structlog

# Importar serviços existentes da camada de domínio
from app.services.system_status_service import system_status_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.optimization_service import OptimizationService, get_optimization_service

from pydantic import BaseModel

logger = structlog.get_logger(__name__)
router = APIRouter()

# Modelos de resposta alinhados com o frontend (front/src/app/services/janus-api.service.ts)
class SystemStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str
    timestamp: Optional[str] = None
    uptime_seconds: Optional[float] = None
    system: Optional[Dict[str, Any]] = None
    process: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None

class ServiceHealthItem(BaseModel):
    key: str
    name: str
    status: str
    metric_text: Optional[str] = None

class WorkerStatusResponse(BaseModel):
    id: str
    status: str
    last_heartbeat: datetime
    tasks_processed: int

class SystemOverviewResponse(BaseModel):
    system_status: SystemStatus
    services_status: List[ServiceHealthItem]
    workers_status: List[WorkerStatusResponse]


@router.get("/overview", response_model=SystemOverviewResponse, summary="System overview")
async def get_system_overview(
    request: Request,
    observability: ObservabilityService = Depends(get_observability_service),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
    llm: LLMService = Depends(get_llm_service),
    optimization: OptimizationService = Depends(get_optimization_service),
):
    try:
        # 1) Status do sistema (sincrono)
        system_status_data = system_status_service.get_system_status()
        sys_status = SystemStatus(**system_status_data)

        # 2) Saúde dos serviços (reusa mesma lógica de /system/health/services)
        agent_h = await observability.get_multi_agent_system_health()
        agent_status = agent_h.get("status", "unknown")
        active_agents = agent_h.get("details", {}).get("active_agents")

        knowledge_h = await knowledge.get_health_status()
        knowledge_status = knowledge_h.get("status", "unknown")
        total_nodes = knowledge_h.get("total_nodes")

        llm_h = await llm.get_health_status()
        llm_status = llm_h.get("status", "unknown")
        llm_details = llm_h.get("details", {})
        open_cb = llm_details.get("open_circuits", 0)
        cached_llms = llm_details.get("cached_llms", 0)

        mem_mb: float = 0.0
        try:
            analysis = await optimization.analyze_system(analysis_type="performance", detailed=False)
            mem_mb = float(analysis.get("metrics_snapshot", {}).get("memory_usage_mb", 0.0))
        except Exception:
            try:
                history = await optimization.get_metrics_history(limit=1)
                if history:
                    last = history[-1]
                    mem_mb = float(getattr(last, "memory_usage_mb", 0.0))
            except Exception:
                mem_mb = 0.0

        memory_status = "ok"
        try:
            if mem_mb >= 8192:
                memory_status = "degraded"
            if mem_mb >= 16384:
                memory_status = "error"
        except Exception:
            memory_status = "ok"

        services_status: List[ServiceHealthItem] = [
            ServiceHealthItem(
                key="agent",
                name="Agent Service",
                status=agent_status,
                metric_text=f"Agentes: {active_agents if active_agents is not None else '—'}",
            ),
            ServiceHealthItem(
                key="knowledge",
                name="Knowledge Service",
                status=knowledge_status,
                metric_text=f"Ontologias: {total_nodes if isinstance(total_nodes, (int, float)) else '—'}",
            ),
            ServiceHealthItem(
                key="memory",
                name="Memory Service",
                status=memory_status,
                metric_text=f"Uso: {int(round(mem_mb))}MB",
            ),
            ServiceHealthItem(
                key="llm",
                name="LLM Gateway",
                status=llm_status,
                metric_text=f"CB Abertos: {open_cb}, Cache: {cached_llms}",
            ),
        ]

        # 3) Status dos workers (transforma saída do orchestrator em shape esperado pelo frontend)
        current = getattr(request.app.state, "orchestrator_workers", []) or []
        now = datetime.now(timezone.utc)
        workers_status: List[WorkerStatusResponse] = []
        for w in current:
            name = w.get("name") or "worker"
            task = w.get("task")
            try:
                running = bool(task and not task.done() and not task.cancelled())
                exc = None
                if task and task.done() and not task.cancelled():
                    try:
                        exc = task.exception()
                    except Exception:
                        exc = None
                status_str = "running" if running else ("error" if exc else "stopped")
            except Exception:
                status_str = "unknown"
            workers_status.append(WorkerStatusResponse(
                id=name,
                status=status_str,
                last_heartbeat=now,
                tasks_processed=0,
            ))

        return SystemOverviewResponse(
            system_status=sys_status,
            services_status=services_status,
            workers_status=workers_status,
        )
    except Exception as e:
        logger.error("Falha ao obter visão geral do sistema", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível obter a visão geral do sistema: {str(e)}"
        )