from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.services.db_migration_service import db_migration_service
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.optimization_service import OptimizationService, get_optimization_service
from app.services.system_health_service import build_service_health_items
from app.services.system_status_service import system_status_service

router = APIRouter()
logger = structlog.get_logger(__name__)


class StatusResponse(BaseModel):
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


class ServiceHealthResponse(BaseModel):
    services: list[ServiceHealthItem]


class UserStatusResponse(BaseModel):
    conversations: int
    messages: int
    approx_in_tokens: int
    approx_out_tokens: int
    vector_points: int


def _degraded_status_response(now: datetime) -> StatusResponse:
    return StatusResponse(
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


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Verifica o estado da aplicacao",
    tags=["System"],
)
async def get_system_status():
    logger.info("Recebida requisicao de status do sistema.")
    try:
        status_data = system_status_service.get_system_status()
        return StatusResponse(**status_data)
    except Exception:
        logger.warning("system_status_collection_unavailable", exc_info=True)
        return _degraded_status_response(datetime.now(UTC))


@router.get(
    "/health/services",
    response_model=ServiceHealthResponse,
    summary="Saude dos microsservicos",
    tags=["System"],
)
async def get_services_health(
    request: Request,
    observability: ObservabilityService = Depends(get_observability_service),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
    llm: LLMService = Depends(get_llm_service),
    optimization: OptimizationService = Depends(get_optimization_service),
):
    workers = getattr(request.app.state, "orchestrator_workers", [])
    services = await build_service_health_items(
        observability,
        knowledge,
        llm,
        optimization,
        workers,
    )
    return ServiceHealthResponse(services=[ServiceHealthItem(**item) for item in services])


@router.get(
    "/status/user",
    response_model=UserStatusResponse,
    summary="Resumo de status por usuario (ator ou admin)",
    tags=["System"],
)
async def get_user_status(
    request: Request,
    user_id: int | None = None,
    observability: ObservabilityService = Depends(get_observability_service),
):
    actor = getattr(request.state, "actor_user_id", None)
    if actor is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    from app.repositories.user_repository import UserRepository

    repo = UserRepository()
    is_admin = False
    try:
        is_admin = repo.is_admin(int(actor))
    except Exception:
        is_admin = False
    target_uid = user_id or str(actor)
    if (not is_admin) and (user_id is not None) and (str(user_id) != str(actor)):
        raise HTTPException(status_code=403, detail="Forbidden")
    metrics = await observability.get_user_metrics(target_uid)
    return UserStatusResponse(**metrics)


@router.get(
    "/db/validate",
    summary="Valida schema Database (users/sessions/messages/profiles)",
    tags=["System"],
)
async def validate_db_schema():
    return db_migration_service.validate_schema()


@router.post(
    "/db/migrate",
    summary="Migra schema Database (cria indices/constraints ausentes)",
    tags=["System"],
)
async def migrate_db_schema():
    return db_migration_service.migrate_schema()
