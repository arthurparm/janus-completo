from typing import Any

import structlog
from fastapi import FastAPI

from app.core.kernel import Kernel

logger = structlog.get_logger(__name__)

KERNEL_STATE_BINDINGS: dict[str, str] = {
    "graph_db": "graph_db",
    "memory_db": "memory_db",
    "broker": "broker",
    "agent_manager": "agent_manager",
    "knowledge_repo": "knowledge_repo",
    "memory_repo": "memory_repo",
    "agent_repo": "agent_repo",
    "task_repo": "task_repo",
    "context_repo": "context_repo",
    "sandbox_repo": "sandbox_repo",
    "tool_repo": "tool_repo",
    "collaboration_repo": "collaboration_repo",
    "llm_repo": "llm_repo",
    "chat_repo": "chat_repo",
    "optimization_repo": "optimization_repo",
    "observability_repo": "observability_repo",
    "reflexion_repo": "reflexion_repo",
    "prompt_repo": "prompt_repo",
    "outbox_repo": "outbox_repo",
    "document_manifest_repo": "document_manifest_repo",
    "agent_service": "agent_service",
    "memory_service": "memory_service",
    "knowledge_service": "knowledge_service",
    "task_service": "task_service",
    "context_service": "context_service",
    "sandbox_service": "sandbox_service",
    "reflexion_service": "reflexion_service",
    "tool_service": "tool_service",
    "collaboration_service": "collaboration_service",
    "document_service": "document_service",
    "observability_service": "observability_service",
    "optimization_service": "optimization_service",
    "autonomy_service": "autonomy_service",
    "llm_service": "llm_service",
    "inference_facade": "inference_facade",
    "chat_service": "chat_service",
    "assistant_service": "assistant_service",
    "outbox_service": "outbox_service",
    "knowledge_facade": "knowledge_facade",
    "prompt_builder_service": "prompt_builder_service",
    "prompt_service": "prompt_service",
    "rag_service": "rag_service",
    "tool_executor": "tool_executor",
    "goal_manager": "goal_manager",
    "scheduler": "scheduler",
    "workers": "workers",
    "config_service": "config_service",
    "voice_manager": "voice_manager",
    "monitor": "monitor",
}


async def bootstrap_infrastructure():
    """Delegates system startup to the Kernel."""
    logger.info("Application startup: bootstrapping via Kernel...")
    kernel = Kernel.get_instance()
    await kernel.startup()


async def shutdown_infrastructure(app: FastAPI):
    """Delegates system shutdown to the Kernel."""
    logger.info("Application shutdown: requesting Kernel shutdown...")
    kernel = Kernel.get_instance()
    await kernel.shutdown()


async def bootstrap_dependencies(app: FastAPI):
    """
    Maps Kernel services to FastAPI app.state to support endpoint dependency injection.
    """
    logger.info("Mapping Kernel dependencies to FastAPI state...")
    kernel = Kernel.get_instance()

    for state_key, kernel_attr in KERNEL_STATE_BINDINGS.items():
        value: Any = getattr(kernel, kernel_attr)
        setattr(app.state, state_key, value)

    logger.info("Kernel dependencies mapped to FastAPI state.")
