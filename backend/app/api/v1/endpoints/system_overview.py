from datetime import UTC, datetime
from typing import Any, Mapping

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.v1.endpoints.workers import _task_status
from app.config import settings
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.optimization_service import OptimizationService, get_optimization_service
from app.services.system_health_service import build_service_health_items
from app.services.system_status_service import system_status_service

logger = structlog.get_logger(__name__)
router = APIRouter()


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
    capability: str | None = None
    user_impact: str | None = None
    recommended_action: str | None = None


class WorkerStatusResponse(BaseModel):
    id: str
    status: str
    last_heartbeat: datetime
    tasks_processed: int


class SystemOverviewResponse(BaseModel):
    system_status: SystemStatus
    services_status: list[ServiceHealthItem]
    workers_status: list[WorkerStatusResponse]


def _build_workers_status(raw_workers: Any, now: datetime) -> list[WorkerStatusResponse]:
    if not isinstance(raw_workers, list):
        logger.warning(
            "system_overview_invalid_workers_collection",
            collection_type=type(raw_workers).__name__,
        )
        return []

    workers_status: list[WorkerStatusResponse] = []
    for index, worker in enumerate(raw_workers):
        if not isinstance(worker, Mapping):
            logger.warning(
                "system_overview_invalid_worker_item",
                index=index,
                item_type=type(worker).__name__,
            )
            continue

        name = worker.get("name") or "worker"
        task = worker.get("task")
        tasks_processed = worker.get("tasks_processed", 0)
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
            logger.warning(
                "system_overview_worker_status_unavailable",
                worker=name,
                exc_info=True,
            )
            status_str = "unknown"
        workers_status.append(
            WorkerStatusResponse(
                id=str(name),
                status=status_str,
                last_heartbeat=now,
                tasks_processed=tasks_processed,
            )
        )

    return workers_status


def _build_system_status(now: datetime) -> SystemStatus:
    try:
        return SystemStatus(**system_status_service.get_system_status())
    except Exception:
        logger.warning("system_overview_system_status_unavailable", exc_info=True)
        return SystemStatus(
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            status="DEGRADED",
            timestamp=now.isoformat(),
            uptime_seconds=None,
            system=None,
            process=None,
            performance={
                "cpu_percent": None,
                "memory_percent": None,
            },
            config=None,
        )


@router.get("/overview", response_model=SystemOverviewResponse, summary="System overview")
async def get_system_overview(
    request: Request,
    observability: ObservabilityService = Depends(get_observability_service),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
    llm: LLMService = Depends(get_llm_service),
    optimization: OptimizationService = Depends(get_optimization_service),
):
    try:
        now = datetime.now(UTC)
        sys_status = _build_system_status(now)
        current = getattr(request.app.state, "orchestrator_workers", []) or []

        service_items = await build_service_health_items(
            observability,
            knowledge,
            llm,
            optimization,
            current,
        )
        services_status = [ServiceHealthItem(**item) for item in service_items]

        workers_status = _build_workers_status(current, now)

        return SystemOverviewResponse(
            system_status=sys_status,
            services_status=services_status,
            workers_status=workers_status,
        )
    except Exception as e:
        logger.error("Falha ao obter visao geral do sistema", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System overview unavailable",
        )
