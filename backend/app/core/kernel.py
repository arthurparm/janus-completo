import asyncio
from typing import Any

import structlog

# Infrastructure
from app.config import settings
from app.core.agents.agent_manager import get_agent_manager

# Core Components
from app.core.autonomy.goal_manager import GoalManager
from app.core.infrastructure import close_broker, get_broker, initialize_broker, setup_logging
from app.core.memory.memory_core import close_memory_db, get_memory_db, initialize_memory_db
from app.core.monitoring import get_health_monitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler
from app.core.senses.audio.manager import VoiceManager
from app.core.tools.os_tools import register_os_tools
from app.core.workers import data_harvester as data_harvester_module
from app.core.workers.async_consolidation_worker import start_consolidation_worker
from app.core.workers.data_harvester import DataHarvester, MemoryConnector
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
from app.core.workers.life_cycle_worker import LifeCycleWorker
from app.core.workers.neural_training_worker import start_neural_training_worker
from app.db.graph import close_graph_db, get_graph_db, initialize_graph_db

# from app.core.infrastructure.auth import get_actor_user_id
from app.db import db
from app.repositories.agent_repository import AgentRepository
from app.repositories.chat_repository_sql import ChatRepositorySQL
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.context_repository import ContextRepository

# Repositories
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.llm_repository import LLMRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.observability_repository import ObservabilityRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.optimization_repository import OptimizationRepository
from app.repositories.reflexion_repository import ReflexionRepository
from app.repositories.sandbox_repository import SandboxRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.tool_repository import ToolRepository
from app.repositories.prompt_repository import PromptRepository

# Services
from app.services.agent_service import AgentService
from app.services.assistant_service import AssistantService
from app.services.autonomy_service import AutonomyService
from app.services.autonomy_lock_service import AutonomyLockService
from app.services.chat_service import ChatService
from app.services.collaboration_service import CollaborationService
from app.services.context_service import ContextService
from app.services.document_service import DocumentIngestionService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.observability_service import ObservabilityService
from app.services.outbox_service import OutboxService
from app.services.optimization_service import OptimizationService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.reflexion_service import ReflexionService
from app.services.sandbox_service import SandboxService
from app.services.scheduler_service import get_scheduler, initialize_default_jobs
from app.services.task_service import TaskService
from app.services.tool_executor_service import ToolExecutorService
from app.services.tool_service import ToolService
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)


class KernelError(Exception):
    """Erro crítico na inicialização do Kernel."""

    pass


class Kernel:
    """
    The Core System Kernel.
    Manages the lifecycle of the application, initializes all components,
    and acts as the central dependency container.
    """

    _instance = None

    def __init__(self):
        # Infrastructure
        self.graph_db = None
        self.memory_db = None
        self.broker = None
        self.agent_manager = None

        # Repositories
        self.knowledge_repo = None
        self.memory_repo = None
        self.agent_repo = None
        self.task_repo = None
        self.context_repo = None
        self.sandbox_repo = None
        self.reflexion_repo = None
        self.tool_repo = None
        self.collaboration_repo = None
        self.llm_repo = None
        self.chat_repo = None
        self.optimization_repo = None
        self.observability_repo = None
        self.prompt_repo = None
        self.outbox_repo = None

        # Services
        self.agent_service: AgentService | None = None
        self.memory_service: MemoryService | None = None
        self.knowledge_service: KnowledgeService | None = None
        self.task_service: TaskService | None = None
        self.context_service: ContextService | None = None
        self.sandbox_service: SandboxService | None = None
        self.reflexion_service: ReflexionService | None = None
        self.tool_service: ToolService | None = None
        self.collaboration_service: CollaborationService | None = None
        self.document_service: DocumentIngestionService | None = None
        self.observability_service: ObservabilityService | None = None
        self.outbox_service: OutboxService | None = None
        self.optimization_service: OptimizationService | None = None
        self.autonomy_service: AutonomyService | None = None
        self.llm_service: LLMService | None = None
        self.chat_service: ChatService | None = None
        self.assistant_service: AssistantService | None = None
        self.prompt_builder_service: PromptBuilderService | None = None
        self.prompt_service: PromptService | None = None
        self.tool_executor: ToolExecutorService | None = None
        self.rag_service: RAGService | None = None

        # Core
        self.goal_manager: GoalManager | None = None
        self.voice_manager: VoiceManager | None = None
        self.monitor = None

        # Workers
        self.workers: list[Any] = []
        self._neural_training_task = None
        self._consolidation_consumer_task = None
        self.scheduler = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Kernel()
        return cls._instance

    async def startup(self):
        """Initializes the entire system in a coordinated sequence."""
        import os

        log_file = "/app/app/janus.log" if os.path.isdir("/app/app") else os.path.join(os.getcwd(), "janus.log")
        setup_logging(log_file=log_file)
        logger.info("Kernel startup: Begin phase 1 (Infrastructure)...")

        try:
            # 1. Infrastructure (Critical)
            await self._init_infrastructure()

            # 2. Actors (Critical)
            await self._init_mas_actors()

            # 3. Dependencies & Services (Critical)
            self._build_dependency_graph()

            # 4. Agentic Capabilities (OS Tools)
            register_os_tools()
            from app.core.ui.ui_tools import register_ui_tools
            register_ui_tools()

            # 5. Workers & Observability
            await self._start_background_processes()

            # 6. Auto-Index (Self-Healing)
            if getattr(settings, "AUTO_INDEX_ON_STARTUP", True):
                asyncio.create_task(self._run_auto_index())

            # 7. Warm-up (Background)
            asyncio.create_task(self._warm_up_llms_async())

            # 8. Senses (Optional)
            await self._init_senses()

            logger.info("Kernel startup complete. System is ready.")
        except KernelError as ke:
            logger.critical("log_critical", message=f"Kernel startup failed: {ke}")
            raise
        except Exception as e:
            logger.critical("log_critical", message=f"Unexpected kernel failure: {e}", exc_info=True)
            raise KernelError(f"Unexpected kernel failure: {e}") from e

    async def _init_infrastructure(self):
        try:
            try:
                await db.create_tables()
            except Exception as e:
                logger.warning("log_warning", message=f"DB table creation skipped or failed: {e}")

            # Initialize Core Infra
            from app.core.infrastructure.redis_manager import RedisManager

            await asyncio.gather(
                initialize_graph_db(),
                initialize_memory_db(),
                initialize_broker(),
                RedisManager.get_instance().initialize(),
            )

            # Initialize Firebase if enabled
            await self._init_firebase()

            self.graph_db = await get_graph_db()
            self.memory_db = await get_memory_db()
            self.broker = await get_broker()
            self.agent_manager = get_agent_manager()

            logger.info("Infrastructure initialized successfully.")
        except Exception as e:
            raise KernelError(f"Infrastructure init failed: {e}") from e

    async def _init_firebase(self):
        if getattr(settings, "FIREBASE_ENABLED", False) and getattr(
            settings, "FIREBASE_CREDENTIALS_PATH", None
        ):
            try:
                from app.core.infrastructure.firebase import get_firebase_service

                cred_path = settings.FIREBASE_CREDENTIALS_PATH
                import os

                if os.path.exists(cred_path):
                    db_url = getattr(settings, "FIREBASE_DATABASE_URL", None)
                    get_firebase_service().initialize(cred_path, db_url)
                    logger.info("Firebase Service initialized.", db_url=db_url)
                else:
                    logger.warning("log_warning", message=f"Firebase credentials missing at {cred_path}")
            except Exception as e:
                logger.error("log_error", message=f"Firebase init failed: {e}")
                # Non-critical, do not raise

    async def _init_senses(self):
        try:
            self.voice_manager = VoiceManager()
            self.voice_manager.initialize()
        except Exception as e:
            logger.warning("log_warning", message=f"Voice Manager failed to initialize: {e}")

    async def shutdown(self):
        """Gracefully shuts down the system."""
        logger.info("Kernel shutdown: Closing resources...")

        # Stop workers
        for worker in self.workers:
            try:
                await worker.stop()
            except Exception as e:
                logger.error("log_error", message=f"Error stopping worker {worker}: {e}")

        # Cancel training task
        if self._neural_training_task:
            self._neural_training_task.cancel()
        if self._consolidation_consumer_task:
            self._consolidation_consumer_task.cancel()

        # Stop monitoring
        if self.monitor:
            try:
                self.monitor.stop_monitoring()
            except Exception:
                pass

        # Stop Scheduler
        if self.scheduler:
            try:
                await self.scheduler.stop()
            except Exception as e:
                logger.error("log_error", message=f"Error stopping scheduler: {e}")

        # Close SQL engines
        try:
            await db.shutdown()
        except Exception as e:
            logger.warning("Error closing database engines during shutdown", exc_info=e)

        # Close Infra
        await asyncio.gather(
            close_graph_db(), close_memory_db(), close_broker(), return_exceptions=True
        )
        logger.info("Kernel shutdown complete.")

    async def _init_mas_actors(self):
        try:
            from app.core.agents.multi_agent_system import AgentRole, get_multi_agent_system
            if not getattr(settings, "INIT_MAS_AGENTS_ON_STARTUP", True):
                logger.info("Multi-Agent System actor init skipped by configuration.")
                return

            mas = get_multi_agent_system()
            await mas.create_agent(AgentRole.PROJECT_MANAGER)
            await mas.create_agent(AgentRole.CODER)
            await mas.create_agent(AgentRole.RESEARCHER)
            await mas.create_agent(AgentRole.SYSADMIN)
            logger.info("Multi-Agent System actors initialized.")
        except Exception as e:
            # Critical because agents are core to operation
            logger.error("log_error", message=f"Failed to initialize Multi-Agent System actors: {e}")
            raise KernelError("Failed to initialize system agents") from e

    def _build_dependency_graph(self):
        logger.info("Building dependency graph...")
        try:
            # Repositories
            self.knowledge_repo = KnowledgeRepository(self.graph_db)
            self.memory_repo = MemoryRepository(self.memory_db)
            self.agent_repo = AgentRepository(self.agent_manager)
            self.task_repo = TaskRepository(self.broker)
            self.context_repo = ContextRepository()
            self.sandbox_repo = SandboxRepository()
            self.tool_repo = ToolRepository()
            self.collaboration_repo = CollaborationRepository()
            self.llm_repo = LLMRepository()
            self.chat_repo = ChatRepositorySQL()
            self.optimization_repo = OptimizationRepository()
            self.prompt_repo = PromptRepository()
            self.outbox_repo = OutboxRepository()

            # Monitoring
            self.monitor = get_health_monitor()
            pp_handler = get_poison_pill_handler()
            self.observability_repo = ObservabilityRepository(self.monitor, pp_handler)

            # Services
            self.agent_service = AgentService(self.agent_repo)
            self.memory_service = MemoryService(self.memory_repo)
            self.knowledge_service = KnowledgeService(self.knowledge_repo)
            self.task_service = TaskService(self.task_repo)
            self.context_service = ContextService(self.context_repo)
            self.sandbox_service = SandboxService(self.sandbox_repo)
            self.reflexion_repo = ReflexionRepository(memory_service=self.memory_service)
            self.reflexion_service = ReflexionService(repo=self.reflexion_repo)
            self.tool_service = ToolService(self.tool_repo)
            self.collaboration_service = CollaborationService(self.collaboration_repo)
            self.document_service = DocumentIngestionService(self.memory_service)
            self.observability_service = ObservabilityService(self.observability_repo)
            self.outbox_service = OutboxService(self.outbox_repo)
            from app.services.chat_event_logger import ChatEventDbLogger

            self.chat_event_logger = ChatEventDbLogger(self.observability_repo)
            self.optimization_service = OptimizationService(self.optimization_repo)
            self.prompt_service = PromptService(self.prompt_repo)

            # Config Service (Hot Reload)
            from app.services.config_service import get_config_service

            self.config_service = get_config_service()
            # Not async start here, it's done in startup

            # Logic Layer
            self.llm_service = LLMService(self.llm_repo, self.prompt_service)
            self.assistant_service = AssistantService(self.llm_service)
            self.goal_manager = GoalManager(self.memory_service)

            self.autonomy_service = AutonomyService(
                self.optimization_service,
                self.llm_service,
                self.goal_manager,
                collaboration_service=self.collaboration_service,
                lock_service=AutonomyLockService(),
            )

            # Chat Stack
            self.prompt_builder_service = PromptBuilderService(self.prompt_service)
            self.tool_executor = ToolExecutorService()
            self.rag_service = RAGService(self.chat_repo, self.llm_service, self.memory_service)
            self.chat_service = ChatService(
                self.chat_repo,
                self.llm_service,
                self.tool_service,
                self.memory_service,
                prompt_service=self.prompt_builder_service,
                tool_executor_service=self.tool_executor,
                rag_service=self.rag_service,
                event_logger=self.chat_event_logger,
                outbox_service=self.outbox_service,
            )
        except Exception as e:
            raise KernelError(f"Dependency injection failed: {e}") from e

    async def _start_background_processes(self):
        logger.info("Initializing background workers...")
        try:
            await self.monitor.check_all_components()
            await self.monitor.start_monitoring(interval_seconds=30)

            # Start Config Service
            if self.config_service:
                await self.config_service.start()

            memory_connector = MemoryConnector(self.memory_repo)
            data_harvester = DataHarvester(connectors=[memory_connector])
            data_harvester_module.harvester = data_harvester

            life_cycle_worker = LifeCycleWorker(
                goal_manager=self.goal_manager, memory_service=self.memory_service
            )

            await knowledge_consolidator.start(limit=10, min_score=0.0)
            await data_harvester.start()
            await life_cycle_worker.start()
            if self.outbox_service:
                await self.outbox_service.start(interval_seconds=5)

            # Async Workers
            try:
                self._consolidation_consumer_task = await start_consolidation_worker()
            except Exception as e:
                logger.error("log_error", message=f"Failed to start async consolidation worker: {e}")

            self._neural_training_task = await start_neural_training_worker()

            self.workers = [
                knowledge_consolidator,
                data_harvester,
                life_cycle_worker,
            ]
            if self.outbox_service is not None:
                self.workers.append(self.outbox_service)

            # Scheduler
            self.scheduler = get_scheduler()
            await initialize_default_jobs(self.scheduler)
            await self.scheduler.start()

        except Exception as e:
            # If workers fail, system is degraded but maybe usable
            logger.error("log_error", message=f"Background process initialization failed: {e}")

            # Register a failing health check so /health endpoint reports the error
            if hasattr(self, "monitor") and self.monitor:
                self.monitor.register_health_check(
                    "background_workers",
                    lambda: {
                        "status": "unhealthy",
                        "message": f"Startup failed: {e}",
                        "details": {"error": str(e)},
                    },
                    is_critical=True,
                )
            pass

    async def _run_auto_index(self):
        """Executa indexação automática e cria usuário admin se necessário."""
        try:
            logger.info("Starting automatic codebase indexation...")
            await self.knowledge_service.index_codebase()

            # Garante admin user
            async with await self.graph_db.get_session() as session:
                await session.run(
                    "MERGE (u:User {name: 'Admin'}) SET u.email = 'admin@janus.system'"
                )

            logger.info("Automatic indexation complete.")
        except Exception as e:
            logger.error("log_error", message=f"Error during automatic indexation: {e}", exc_info=True)

    async def _warm_up_llms_async(self):
        """Warm up LLMs in a separate thread to avoid blocking the event loop."""
        try:
            warm_specs = getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or []
            if warm_specs and self.llm_service:
                logger.info("Starting background LLM pool warm-up...")
                # Run the synchronous warm_pool in a thread
                warmed = await asyncio.to_thread(self.llm_service.warm_pool, warm_specs)
                logger.info("log_info", message=f"Background LLM warm-up complete. Warmed: {warmed}")
        except Exception as e:
            logger.warning("log_warning", message=f"Background LLM warm-up failed (non-critical): {e}")
