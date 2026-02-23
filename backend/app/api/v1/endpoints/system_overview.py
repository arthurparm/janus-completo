from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.v1.endpoints.workers import _task_status
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.optimization_service import OptimizationService, get_optimization_service

# Importar serviÃ§os existentes da camada de domÃ­nio
from app.services.system_status_service import system_status_service

logger = structlog.get_logger(__name__)
router = APIRouter()


# Modelos de resposta alinhados com o frontend (frontend/src/app/services/backend-api.service.ts)
class SystemStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str
    timestamp: str | None = None
    uptime_seconds: float | None = None
    system: dict[str, Any] | None = None
    process: dict[str, Any] | None = None
    performance: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class ServiceHealthItem(BaseModel):
    key: str
    name: str
    status: str
    metric_text: str | None = None


class WorkerStatusResponse(BaseModel):
    id: str
    status: str
    last_heartbeat: datetime
    tasks_processed: int


class SystemOverviewResponse(BaseModel):
    system_status: SystemStatus
    services_status: list[ServiceHealthItem]
    workers_status: list[WorkerStatusResponse]


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

        # 2) SaÃºde dos serviÃ§os (reusa mesma lÃ³gica de /system/health/services)
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
            analysis = await optimization.analyze_system(
                analysis_type="performance", detailed=False
            )
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

        services_status: list[ServiceHealthItem] = [
            ServiceHealthItem(
                key="agent",
                name="Agent Service",
                status=agent_status,
                metric_text=f"Agentes: {active_agents if active_agents is not None else 'N/A'}",
            ),
            ServiceHealthItem(
                key="knowledge",
                name="Knowledge Service",
                status=knowledge_status,
                metric_text=f"Ontologias: {total_nodes if isinstance(total_nodes, (int, float)) else 'N/A'}",
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

        # 3) Status dos workers (transforma saÃ­da do orchestrator em shape esperado pelo frontend)
        current = getattr(request.app.state, "orchestrator_workers", []) or []
        now = datetime.now(UTC)
        workers_status: list[WorkerStatusResponse] = []
        for w in current:
            name = w.get("name") or "worker"
            task = w.get("task")
            tasks_processed = w.get("tasks_processed", 0)
            if not isinstance(tasks_processed, int):
                tasks_processed = 0
            try:
                status_payload = _task_status(task)
                if status_payload.get("state") == "disabled":
                    status_str = "disabled"
                elif status_payload.get("running"):
                    status_str = "running"
                elif status_payload.get("exception"):
                    status_str = "error"
                elif status_payload.get("state") == "unknown":
                    status_str = "unknown"
                else:
                    status_str = "stopped"
            except Exception:
                status_str = "unknown"
            workers_status.append(
                WorkerStatusResponse(
                    id=name,
                    status=status_str,
                    last_heartbeat=now,
                    tasks_processed=tasks_processed,
                )
            )

        return SystemOverviewResponse(
            system_status=sys_status,
            services_status=services_status,
            workers_status=workers_status,
        )
    except Exception as e:
        logger.error("Falha ao obter visÃ£o geral do sistema", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System overview unavailable",
        )
