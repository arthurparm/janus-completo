"""
Orquestrador de Workers

Centraliza a inicialização de todos os workers e tarefas em background
usando imports lazy para evitar ciclos de importação.
"""
import structlog
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = structlog.get_logger(__name__)

WORKER_NAMES: list[str] = [
    "memory_maintenance",
    "knowledge_consolidation",
    "document_ingestion",
    "agent_tasks",
    "neural_training",
    "reflexion",
    "meta_agent",
    "failure_consumer",
    "auto_scaler",
    "auto_healer",
    "router",
    "code_agent",
    "red_team_agent",
    "professor_agent",
    "sandbox_agent",
    "thinker_agent",
    "distillation",
    "google_productivity",
    "debate_proponent",
    "debate_critic",
    "codex_worker",
]

NODE_PROFILE_WORKERS: dict[str, set[str]] = {
    "INFERENCE_HEAVY": {
        "neural_training",
        "reflexion",
        "thinker_agent",
        "code_agent",
    },
    "INTELLIGENCE_AGILE": {
        "knowledge_consolidation",
        "document_ingestion",
        "distillation",
    },
    "CORE_INFRA": {
        "memory_maintenance",
        "auto_scaler",
        "auto_healer",
        "router",
    },
}


def get_orchestrator_worker_names() -> list[str]:
    return list(WORKER_NAMES)


@dataclass(frozen=True)
class DisabledWorkerHandle:
    """Representa um worker intencionalmente desativado por configuração."""

    reason: str = "disabled_by_config"
    detail: str | None = None


def _normalize_node_profile(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def _get_active_node_profile() -> str | None:
    profile = _normalize_node_profile(getattr(settings, "JANUS_NODE_PROFILE", None))
    if profile is None:
        return None
    if profile not in NODE_PROFILE_WORKERS:
        logger.warning(
            "log_warning",
            message=(
                f"JANUS_NODE_PROFILE='{profile}' é inválido. "
                "Iniciando todos os workers por compatibilidade."
            ),
        )
        return None
    return profile


def _is_worker_enabled_for_profile(worker_name: str, profile: str | None) -> bool:
    if profile is None:
        return True
    return worker_name in NODE_PROFILE_WORKERS.get(profile, set())


async def start_all_workers():
    """
    Inicia todos os workers assíncronos do sistema.
    Retorna a lista de tarefas/consumidores iniciados.
    """
    # Imports lazy para evitar ciclos entre módulos de workers/monitoring
    from app.core.monitoring import start_auto_healer
    from app.core.workers.agent_tasks_worker import start_agent_tasks_worker
    from app.core.workers.async_consolidation_worker import start_consolidation_worker
    from app.core.workers.auto_scaler import start_auto_scaler
    from app.core.workers.code_agent_worker import start_code_agent_worker
    from app.core.workers.codex_worker import start_codex_worker
    from app.core.workers.document_ingestion_worker import start_document_ingestion_worker
    from app.core.workers.distillation_worker import start_distillation_worker
    from app.core.workers.debate_proponent_worker import start_debate_proponent_worker
    from app.core.workers.debate_critic_worker import start_debate_critic_worker
    from app.core.workers.meta_agent_worker import (
        start_failure_event_consumer,
        start_meta_agent_worker,
    )
    from app.core.workers.neural_training_worker import start_neural_training_worker
    from app.core.workers.professor_agent_worker import start_professor_agent_worker
    from app.core.workers.red_team_agent_worker import start_red_team_agent_worker
    from app.core.workers.reflexion_worker import start_reflexion_worker
    from app.core.workers.router_worker import start_router_worker
    from app.core.workers.sandbox_agent_worker import start_sandbox_agent_worker
    from app.core.workers.thinker_agent_worker import start_thinker_agent_worker
    from app.core.workers.memory_maintenance_worker import memory_maintenance_worker

    active_profile = _get_active_node_profile()
    logger.info(
        "Iniciando orquestrador de workers...",
        node_profile=active_profile or "ALL",
    )

    workers: list[Any] = []
    async def _start_memory_maintenance():
        await memory_maintenance_worker.start()
        return memory_maintenance_worker.task

    async def _start_google_productivity():
        from app.core.workers.google_productivity_worker import start_google_productivity_consumer

        return await start_google_productivity_consumer()

    worker_starters: dict[str, Any] = {
        "memory_maintenance": _start_memory_maintenance,
        "knowledge_consolidation": start_consolidation_worker,
        "document_ingestion": start_document_ingestion_worker,
        "agent_tasks": start_agent_tasks_worker,
        "neural_training": start_neural_training_worker,
        "reflexion": start_reflexion_worker,
        "meta_agent": start_meta_agent_worker,
        "failure_consumer": start_failure_event_consumer,
        "auto_scaler": start_auto_scaler,
        "auto_healer": start_auto_healer,
        "router": start_router_worker,
        "code_agent": start_code_agent_worker,
        "red_team_agent": start_red_team_agent_worker,
        "professor_agent": start_professor_agent_worker,
        "sandbox_agent": start_sandbox_agent_worker,
        "thinker_agent": start_thinker_agent_worker,
        "distillation": start_distillation_worker,
        "google_productivity": _start_google_productivity,
        "debate_proponent": start_debate_proponent_worker,
        "debate_critic": start_debate_critic_worker,
        "codex_worker": start_codex_worker,
    }

    for worker_name in WORKER_NAMES:
        if not _is_worker_enabled_for_profile(worker_name, active_profile):
            workers.append(
                DisabledWorkerHandle(
                    reason="disabled_by_profile",
                    detail=f"JANUS_NODE_PROFILE={active_profile}",
                )
            )
            logger.info(
                f"Worker {worker_name} desativado por perfil de nó.",
                node_profile=active_profile,
            )
            continue

        if worker_name == "google_productivity" and not getattr(
            settings, "ENABLE_GOOGLE_PRODUCTIVITY_WORKER", False
        ):
            workers.append(
                DisabledWorkerHandle(
                    detail="ENABLE_GOOGLE_PRODUCTIVITY_WORKER=false",
                )
            )
            logger.info("Worker google_productivity desativado por configuracao.")
            continue

        starter = worker_starters[worker_name]
        workers.append(await starter())

    logger.info("log_info", message=f"✓ {len(workers)} workers iniciados pelo orquestrador.")
    return workers
