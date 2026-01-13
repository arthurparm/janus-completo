import asyncio
import structlog
from fastapi import FastAPI

from app.core.kernel import Kernel

logger = structlog.get_logger(__name__)


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
    Maps Kernel services to FastAPI app.state for backward compatibility
    and dependency injection support in endpoints.
    """
    logger.info("Mapping Kernel dependencies to FastAPI state...")
    kernel = Kernel.get_instance()

    # Infrastructure
    app.state.graph_db = kernel.graph_db
    app.state.memory_db = kernel.memory_db
    app.state.broker = kernel.broker
    app.state.agent_manager = kernel.agent_manager

    # Repositories
    app.state.knowledge_repo = kernel.knowledge_repo
    app.state.memory_repo = kernel.memory_repo
    app.state.agent_repo = kernel.agent_repo
    app.state.task_repo = kernel.task_repo
    app.state.context_repo = kernel.context_repo
    app.state.sandbox_repo = kernel.sandbox_repo
    app.state.tool_repo = kernel.tool_repo
    app.state.collaboration_repo = kernel.collaboration_repo
    app.state.llm_repo = kernel.llm_repo
    app.state.chat_repo = kernel.chat_repo
    app.state.optimization_repo = kernel.optimization_repo
    app.state.observability_repo = kernel.observability_repo
    app.state.reflexion_repo = kernel.reflexion_repo

    # Services
    app.state.agent_service = kernel.agent_service
    app.state.memory_service = kernel.memory_service
    app.state.knowledge_service = kernel.knowledge_service
    app.state.task_service = kernel.task_service
    app.state.context_service = kernel.context_service
    app.state.sandbox_service = kernel.sandbox_service
    app.state.reflexion_service = kernel.reflexion_service
    app.state.tool_service = kernel.tool_service
    app.state.collaboration_service = kernel.collaboration_service
    app.state.document_service = kernel.document_service
    app.state.observability_service = kernel.observability_service
    app.state.optimization_service = kernel.optimization_service
    app.state.autonomy_service = kernel.autonomy_service
    app.state.llm_service = kernel.llm_service
    app.state.chat_service = kernel.chat_service
    app.state.assistant_service = kernel.assistant_service

    # Core Components
    app.state.goal_manager = kernel.goal_manager
    app.state.scheduler = kernel.scheduler

    # Workers (referência apenas, gerenciados pelo Kernel)
    app.state.workers = kernel.workers

    # Config Service
    app.state.config_service = kernel.config_service

    logger.info("Kernel dependencies mapped to FastAPI state.")
