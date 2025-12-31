import asyncio
import structlog
from typing import Optional, List, Any

# Infrastructure
from app.config import settings
from app.core.infrastructure import (
    initialize_broker, close_broker, get_broker,
    setup_logging
)
from app.db.graph import initialize_graph_db, close_graph_db, get_graph_db
from app.core.memory.memory_core import initialize_memory_db, close_memory_db, get_memory_db
# from app.core.infrastructure.auth import get_actor_user_id
from app.db.mysql_config import init_mysql_database
from app.core.monitoring import get_health_monitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler
from app.core.tools.os_tools import register_os_tools

# Repositories
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

# Services
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

# Core Components
from app.core.autonomy.goal_manager import GoalManager
from app.core.agents.agent_manager import get_agent_manager
from app.core.workers.knowledge_consolidator import KnowledgeConsolidator
from app.core.workers.data_harvester import DataHarvester, MemoryConnector
from app.core.workers import data_harvester as data_harvester_module
from app.core.workers.neural_training_worker import start_neural_training_worker
from app.core.workers.life_cycle_worker import LifeCycleWorker
from app.core.senses.audio.manager import VoiceManager
from app.core.agents.meta_agent_worker import MetaAgentWorker
from app.core.workers.async_consolidation_worker import start_consolidation_worker
from app.services.scheduler_service import get_scheduler, initialize_default_jobs

logger = structlog.get_logger(__name__)

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
        
        # Services
        self.agent_service: Optional[AgentService] = None
        self.memory_service: Optional[MemoryService] = None
        self.knowledge_service: Optional[KnowledgeService] = None
        self.task_service: Optional[TaskService] = None
        self.context_service: Optional[ContextService] = None
        self.sandbox_service: Optional[SandboxService] = None
        self.reflexion_service: Optional[ReflexionService] = None
        self.tool_service: Optional[ToolService] = None
        self.collaboration_service: Optional[CollaborationService] = None
        self.document_service: Optional[DocumentIngestionService] = None
        self.observability_service: Optional[ObservabilityService] = None
        self.optimization_service: Optional[OptimizationService] = None
        self.autonomy_service: Optional[AutonomyService] = None
        self.llm_service: Optional[LLMService] = None
        self.chat_service: Optional[ChatService] = None
        self.assistant_service: Optional[AssistantService] = None
        
        # Core
        self.goal_manager: Optional[GoalManager] = None
        self.voice_manager: Optional[VoiceManager] = None
        self.monitor = None
        
        # Workers
        self.workers: List[Any] = []
        self._neural_training_task = None
        self._consolidation_consumer_task = None
        self.scheduler = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Kernel()
        return cls._instance

    async def startup(self):
        """Initializes the entire system."""
        setup_logging()
        logger.info("Kernel startup: Initializing infrastructure...")
        
        # 1. Infrastructure
        try:
            try:
                init_mysql_database()
            except Exception:
                logger.warning("MySQL init failed; proceeding without auto-create tables.")
            
            await asyncio.gather(
                initialize_graph_db(), 
                initialize_memory_db(), 
                initialize_broker()
            )
            
            # Initialize Firebase if enabled (Sync, as library is mostly sync/HTTP)
            if getattr(settings, "FIREBASE_ENABLED", False) and getattr(settings, "FIREBASE_CREDENTIALS_PATH", None):
                try:
                    from app.core.infrastructure.firebase import get_firebase_service
                    cred_path = settings.FIREBASE_CREDENTIALS_PATH
                    import os
                    if os.path.exists(cred_path):
                        db_url = getattr(settings, "FIREBASE_DATABASE_URL", None)
                        get_firebase_service().initialize(cred_path, db_url)
                        logger.info("Firebase Service initialized in Kernel.", db_url=db_url)
                    else:
                        logger.warning("Firebase credentials not found.", path=cred_path)
                except Exception as fb_err:
                    logger.error("Firebase init failed", error=str(fb_err))
            
            self.graph_db = await get_graph_db()
            self.memory_db = await get_memory_db()
            self.broker = await get_broker()
            self.agent_manager = get_agent_manager()
            
            logger.info("Infrastructure initialized successfully.")
        except Exception as e:
            logger.critical(f"Critical failure during infrastructure initialization: {e}", exc_info=True)
            raise

        # 2. Multi-Agent System (Actors)
        await self._init_mas_actors()

        # 3. Dependencies & Services
        self._build_dependency_graph()
        
        # Register OS Tools (Dangerous) - Enable Agentic Capabilities
        register_os_tools()

        # 4. Observability & Workers
        await self._start_background_processes()
        
        # 5. Background Warm-up (Non-blocking)
        asyncio.create_task(self._warm_up_llms_async())

        
        # 5. Senses (Voice)
        try:
            self.voice_manager = VoiceManager()
            self.voice_manager.initialize()
        except Exception:
            logger.warning("Voice Manager failed to initialize.")

        logger.info("Kernel startup complete. System is ready.")

    async def shutdown(self):
        """Gracefully shuts down the system."""
        logger.info("Kernel shutdown: Closing resources...")
        
        # Stop workers
        for worker in self.workers:
            await worker.stop()
            
        # Cancel training task
        try:
            if self._neural_training_task:
                self._neural_training_task.cancel()
            
            if self._consolidation_consumer_task:
                self._consolidation_consumer_task.cancel()
                # await self._consolidation_consumer_task # Optional
        except Exception:
            pass

        # Stop monitoring
        if self.monitor:
            self.monitor.stop_monitoring()

        # Stop Scheduler
        if self.scheduler:
            await self.scheduler.stop()

        # Close Infra
        await asyncio.gather(
            close_graph_db(), 
            close_memory_db(), 
            close_broker()
        )
        logger.info("Kernel shutdown complete.")

    async def _init_mas_actors(self):
        try:
            from app.core.agents.multi_agent_system import get_multi_agent_system, AgentRole
            mas = get_multi_agent_system()
            mas.create_agent(AgentRole.PROJECT_MANAGER)
            mas.create_agent(AgentRole.CODER)
            mas.create_agent(AgentRole.RESEARCHER)
            mas.create_agent(AgentRole.SYSADMIN)
            logger.info("Multi-Agent System actors initialized.")
        except Exception as e:
            logger.warning(f"Failed to initialize Multi-Agent System actors: {e}")

    def _build_dependency_graph(self):
        logger.info("Building dependency graph...")
        
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
        self.optimization_service = OptimizationService(self.optimization_repo)
        
        self.llm_service = LLMService(self.llm_repo)
        self.assistant_service = AssistantService(self.llm_service)
        
        # Warmup LLM moved to startup background task
        pass
            
        # Goal Manager
        self.goal_manager = GoalManager(self.memory_service)
        
        # Autonomy
        self.autonomy_service = AutonomyService(
            self.optimization_service,
            self.llm_service,
            self.goal_manager,
        )
        
        # Chat
        self.chat_service = ChatService(
            self.chat_repo, 
            self.llm_service, 
            self.tool_service, 
            self.memory_service
        )

    async def _start_background_processes(self):
        logger.info("Initializing background workers...")
        
        await self.monitor.check_all_components()
        await self.monitor.start_monitoring(interval_seconds=30)
        
        knowledge_consolidator = KnowledgeConsolidator(
            agent_service=self.agent_service,
            memory_service=self.memory_service,
            knowledge_repo=self.knowledge_repo,
            llm_service=self.llm_service
        )

        memory_connector = MemoryConnector(self.memory_repo)
        data_harvester = DataHarvester(connectors=[memory_connector])
        data_harvester_module.harvester = data_harvester
        
        life_cycle_worker = LifeCycleWorker(
            goal_manager=self.goal_manager,
            memory_service=self.memory_service
        )

        await knowledge_consolidator.start()
        await data_harvester.start()
        await life_cycle_worker.start()

        # Start Async Knowledge Consolidation Worker (RabbitMQ Consumer)
        try:
            self._consolidation_consumer_task = await start_consolidation_worker()
            logger.info("Async consolidation worker started.")
        except Exception as e:
            logger.error(f"Failed to start async consolidation worker: {e}")
        
        # Meta Agent Worker (Persistent Supervisor)
        meta_agent_interval = int(getattr(settings, "META_AGENT_CYCLE_INTERVAL_SECONDS", 3600))
        meta_agent_worker = MetaAgentWorker(interval_seconds=meta_agent_interval)
        await meta_agent_worker.start()
        
        self._neural_training_task = await start_neural_training_worker()

        self.workers = [knowledge_consolidator, data_harvester, life_cycle_worker, meta_agent_worker]
        
        # Scheduler Service (Cron Jobs)
        self.scheduler = get_scheduler()
        await initialize_default_jobs(self.scheduler)
        await self.scheduler.start()
        logger.info("Scheduler service started with default jobs.")

        # 5. Auto-Index Codebase (Self-Healing)
        if getattr(settings, "AUTO_INDEX_ON_STARTUP", True):
            try:
                stats = await self.knowledge_service.get_stats()
                total_nodes = stats.get("total_nodes", 0)
                # Se tivermos poucos nós (apenas RelationshipType), indexamos
                if total_nodes < 50:
                    logger.warning(f"Graph looks empty ({total_nodes} nodes). Triggering auto-indexation...")
                    # Executamos em background para não bloquear o startup completamente,
                    # Mas se preferir consistência imediata, poderia ser await.
                    # Vamos usar create_task para não atrasar o healthcheck do k8s/docker
                    asyncio.create_task(self._run_auto_index())
            except Exception as e:
                logger.error(f"Failed to check/trigger auto-index: {e}")

    async def _run_auto_index(self):
        """Executa indexação automática e cria usuário admin se necessário."""
        try:
            logger.info("Starting automatic codebase indexation...")
            await self.knowledge_service.index_codebase()
            
            # Garante admin user
            async with await self.graph_db.get_session() as session:
                await session.run("MERGE (u:User {name: 'Admin'}) SET u.email = 'admin@janus.system'")
                
            logger.info("Automatic indexation complete.")
        except Exception as e:
            logger.error(f"Error during automatic indexation: {e}", exc_info=True)

    async def _warm_up_llms_async(self):
        """Warm up LLMs in a separate thread to avoid blocking the event loop."""
        try:
            warm_specs = getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or []
            if warm_specs and self.llm_service:
                logger.info("Starting background LLM pool warm-up...")
                # Run the synchronous warm_pool in a thread
                warmed = await asyncio.to_thread(self.llm_service.warm_pool, warm_specs)
                logger.info(f"Background LLM warm-up complete. Warmed: {warmed}")
        except Exception as e:
            logger.warning(f"Background LLM warm-up failed (non-critical): {e}")
