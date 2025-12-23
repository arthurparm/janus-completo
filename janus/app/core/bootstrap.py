import asyncio
import contextlib
import structlog
from fastapi import FastAPI

from app.config import settings
from app.core.infrastructure import (
    initialize_broker, close_broker, get_broker
)
from app.core.infrastructure.auth import get_actor_user_id
from app.db.graph import initialize_graph_db, close_graph_db, get_graph_db
from app.db.mysql_config import init_mysql_database
from app.models import user_models
from app.core.memory.memory_core import initialize_memory_db, close_memory_db, get_memory_db

from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.agent_repository import AgentRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.context_repository import ContextRepository
from app.repositories.sandbox_repository import SandboxRepository
from app.repositories.reflexion_repository import ReflexionRepository
from app.repositories.tool_repository import ToolRepository
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.observability_repository import ObservabilityRepository
from app.repositories.optimization_repository import OptimizationRepository
from app.repositories.llm_repository import LLMRepository
from app.repositories.chat_repository_sql import ChatRepositorySQL

from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.knowledge_service import KnowledgeService
from app.services.task_service import TaskService
from app.services.context_service import ContextService
from app.services.sandbox_service import SandboxService
from app.services.reflexion_service import ReflexionService
from app.services.tool_service import ToolService
from app.services.collaboration_service import CollaborationService
from app.services.document_service import DocumentIngestionService
from app.services.observability_service import ObservabilityService
from app.services.optimization_service import OptimizationService
from app.services.autonomy_service import AutonomyService
from app.services.llm_service import LLMService
from app.services.chat_service import ChatService
from app.services.assistant_service import AssistantService

from app.core.monitoring import get_health_monitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler
from app.core.autonomy.goal_manager import GoalManager

from app.core.agents.agent_manager import get_agent_manager
from app.core.workers.knowledge_consolidator import KnowledgeConsolidator
from app.core.workers.data_harvester import DataHarvester, MemoryConnector
from app.core.workers import data_harvester as data_harvester_module
from app.core.workers.neural_training_worker import start_neural_training_worker
from app.core.workers.life_cycle_worker import LifeCycleWorker

logger = structlog.get_logger(__name__)

async def bootstrap_infrastructure():
    logger.info("Application startup: Initializing infrastructure...")
    try:
        try:
            init_mysql_database()
        except Exception:
            logger.warning("MySQL init falhou; prosseguindo sem criar tabelas automaticamente.")
        await asyncio.gather(initialize_graph_db(), initialize_memory_db(), initialize_broker())
        logger.info("Infrastructure initialized successfully.")
    except Exception as e:
        logger.critical(f"Critical failure during infrastructure initialization: {e}", exc_info=True)
        raise

async def shutdown_infrastructure(app: FastAPI):
    logger.info("Application shutdown: Closing resources...")
    for worker in getattr(app.state, "workers", []):
        await worker.stop()

    # Cancela consumidor de treinamento
    try:
        if getattr(app.state, "neural_training_consumer_task", None):
            app.state.neural_training_consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await app.state.neural_training_consumer_task
    except Exception:
        pass
    
    # Para o monitoramento
    monitor = get_health_monitor()
    monitor.stop_monitoring()

    await asyncio.gather(close_graph_db(), close_memory_db(), close_broker())
    logger.info("Infrastructure connections closed.")


async def bootstrap_dependencies(app: FastAPI):
    logger.info("Building and sharing dependency graph...")

    # --- Camada de Infraestrutura ---
    graph_db_instance = await get_graph_db()
    memory_db_instance = await get_memory_db()
    broker_instance = await get_broker()
    agent_manager_instance = get_agent_manager()
    
    # Inicializa o Sistema Multi-Agente (Atores)
    try:
        from app.core.agents.multi_agent_system import get_multi_agent_system, AgentRole
        mas = get_multi_agent_system()
        # Inicia atores padrão para estarem prontos para tarefas
        mas.create_agent(AgentRole.PROJECT_MANAGER)
        mas.create_agent(AgentRole.CODER)
        mas.create_agent(AgentRole.RESEARCHER)
        # Outros agentes serão criados sob demanda ou aqui
        logger.info("Multi-Agent System actors initialized.")
    except Exception as e:
        logger.warning(f"Failed to initialize Multi-Agent System actors: {e}")

    # --- Camada de Repositório ---
    app.state.knowledge_repo = KnowledgeRepository(graph_db_instance)
    app.state.memory_repo = MemoryRepository(memory_db_instance)
    app.state.agent_repo = AgentRepository(agent_manager_instance)
    app.state.task_repo = TaskRepository(broker_instance)
    app.state.context_repo = ContextRepository()
    app.state.sandbox_repo = SandboxRepository()
    app.state.tool_repo = ToolRepository()
    app.state.collaboration_repo = CollaborationRepository()

    # --- Camada de Serviço ---
    app.state.agent_service = AgentService(app.state.agent_repo)
    app.state.memory_service = MemoryService(app.state.memory_repo)
    app.state.knowledge_service = KnowledgeService(app.state.knowledge_repo)
    app.state.task_service = TaskService(app.state.task_repo)
    app.state.context_service = ContextService(app.state.context_repo)
    app.state.sandbox_service = SandboxService(app.state.sandbox_repo)
    app.state.reflexion_repo = ReflexionRepository(memory_service=app.state.memory_service)
    app.state.reflexion_service = ReflexionService(repo=app.state.reflexion_repo)
    app.state.tool_service = ToolService(app.state.tool_repo)
    app.state.collaboration_service = CollaborationService(app.state.collaboration_repo)
    app.state.document_service = DocumentIngestionService(app.state.memory_service)
    
    # LLM
    app.state.llm_repo = LLMRepository()
    app.state.llm_service = LLMService(app.state.llm_repo)
    app.state.assistant_service = AssistantService(app.state.llm_service)

    try:
        warm_specs = getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or []
        if warm_specs:
            app.state.llm_service.warm_pool(warm_specs)
    except Exception:
        pass

    # Goals Manager
    app.state.goal_manager = GoalManager(app.state.memory_service)

    # Chat
    app.state.chat_repo = ChatRepositorySQL()
    app.state.chat_service = ChatService(app.state.chat_repo, app.state.llm_service, app.state.tool_service, app.state.memory_service)

    # Self-Optimization
    app.state.optimization_repo = OptimizationRepository()
    app.state.optimization_service = OptimizationService(app.state.optimization_repo)

    # Autonomy Service
    app.state.autonomy_service = AutonomyService(
        app.state.optimization_service,
        app.state.llm_service,
        app.state.goal_manager,
    )

    # Observabilidade
    monitor = get_health_monitor()
    pp_handler = get_poison_pill_handler()
    app.state.observability_repo = ObservabilityRepository(monitor, pp_handler)
    app.state.observability_service = ObservabilityService(app.state.observability_repo)

    await monitor.check_all_components()
    await monitor.start_monitoring(interval_seconds=30)
    
    # Initialize Workers
    logger.info("Initializing and starting background workers...")
    knowledge_consolidator = KnowledgeConsolidator(
        agent_service=app.state.agent_service,
        memory_service=app.state.memory_service,
        knowledge_repo=app.state.knowledge_repo,
        llm_service=app.state.llm_service
    )

    memory_connector = MemoryConnector(app.state.memory_repo)
    data_harvester = DataHarvester(connectors=[memory_connector])
    data_harvester_module.harvester = data_harvester
    
    life_cycle_worker = LifeCycleWorker(
        goal_manager=app.state.goal_manager,
        memory_service=app.state.memory_service
    )

    await knowledge_consolidator.start()
    await data_harvester.start()
    await life_cycle_worker.start()
    neural_training_task = await start_neural_training_worker()

    app.state.workers = [knowledge_consolidator, data_harvester, life_cycle_worker]
    app.state.neural_training_consumer_task = neural_training_task
    
    logger.info("Application startup complete.")
