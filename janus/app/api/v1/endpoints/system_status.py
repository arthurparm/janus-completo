from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.db.mysql_config import init_mysql_database
from app.services.db_migration_service import db_migration_service
from app.services.knowledge_service import KnowledgeService, get_knowledge_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.optimization_service import OptimizationService, get_optimization_service
from app.services.system_status_service import system_status_service

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Model (DTO) ---


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


class ServiceHealthResponse(BaseModel):
    services: list[ServiceHealthItem]


class UserStatusResponse(BaseModel):
    user_id: str
    conversations: int
    messages: int
    approx_in_tokens: int
    approx_out_tokens: int
    vector_points: int


# --- Endpoints ---


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Verifica o estado da aplicação",
    tags=["System"],
)
async def get_system_status():
    """Delega a obtenção do status da aplicação para o SystemStatusService."""
    logger.info("Recebida requisição de status do sistema.")
    status_data = system_status_service.get_system_status()
    return StatusResponse(**status_data)


@router.get(
    "/health/services",
    response_model=ServiceHealthResponse,
    summary="Saúde dos microsserviços",
    tags=["System"],
)
async def get_services_health(
    observability: ObservabilityService = Depends(get_observability_service),
    knowledge: KnowledgeService = Depends(get_knowledge_service),
    llm: LLMService = Depends(get_llm_service),
    optimization: OptimizationService = Depends(get_optimization_service),
):
    # Agent/Multi-Agent System
    agent_h = await observability.get_multi_agent_system_health()
    agent_status = agent_h.get("status", "unknown")
    active_agents = agent_h.get("details", {}).get("active_agents")

    # Knowledge Graph
    knowledge_h = await knowledge.get_health_status()
    knowledge_status = knowledge_h.get("status", "unknown")
    total_nodes = knowledge_h.get("total_nodes")

    # LLM Manager
    llm_h = await llm.get_health_status()
    llm_status = llm_h.get("status", "unknown")
    llm_details = llm_h.get("details", {})
    open_cb = llm_details.get("open_circuits", 0)
    cached_llms = llm_details.get("cached_llms", 0)

    # Memory (System RAM usage via optimization metrics)
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

    # Simple heuristic for memory status
    memory_status = "ok"
    try:
        if mem_mb >= 8192:
            memory_status = "degraded"
        if mem_mb >= 16384:
            memory_status = "error"
    except Exception:
        memory_status = "ok"

    services = [
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

    return ServiceHealthResponse(services=services)


@router.get(
    "/status/user",
    response_model=UserStatusResponse,
    summary="Resumo de status por usuário (ator ou admin)",
    tags=["System"],
)
async def get_user_status(
    request: Request,
    user_id: str | None = None,
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
    m = observability.get_user_metrics(target_uid)
    return UserStatusResponse(**m)


@router.post(
    "/init/mysql", summary="Inicializa tabelas MySQL (cria se não existirem)", tags=["System"]
)
async def init_mysql():
    try:
        init_mysql_database()
        return {"status": "ok"}
    except Exception as e:
        logger.error("Falha ao inicializar MySQL", exc_info=e)
        return {"status": "error", "detail": str(e)}


@router.get(
    "/db/validate",
    summary="Valida schema MySQL (users/sessions/messages/profiles)",
    tags=["System"],
)
async def validate_db_schema():
    return db_migration_service.validate_schema()


@router.post(
    "/db/migrate", summary="Migra schema MySQL (cria índices/constraints ausentes)", tags=["System"]
)
async def migrate_db_schema():
    return db_migration_service.migrate_schema()
