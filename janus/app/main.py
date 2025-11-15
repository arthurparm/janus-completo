import asyncio
import contextlib
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import msgpack
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.exception_handlers import add_exception_handlers
from app.api.v1.router import api_router
from app.config import settings

# Importa os inicializadores de infraestrutura
from app.core.infrastructure import (
    CorrelationMiddleware, RateLimitMiddleware, setup_logging, setup_tracing,
    initialize_broker, close_broker, get_broker
)
from app.core.infrastructure.auth import get_actor_user_id
from app.db.graph import initialize_graph_db, close_graph_db, get_graph_db
from app.db.mysql_config import init_mysql_database
from app.models import user_models  # noqa: F401
from app.core.memory.memory_core import initialize_memory_db, close_memory_db, get_memory_db

# Importa as classes e getters para a construção do grafo de dependências
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.agent_repository import AgentRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.context_repository import ContextRepository
from app.repositories.sandbox_repository import SandboxRepository
from app.repositories.reflexion_repository import ReflexionRepository
from app.repositories.tool_repository import ToolRepository
from app.repositories.collaboration_repository import CollaborationRepository

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
from app.repositories.observability_repository import ObservabilityRepository
from app.core.monitoring import get_health_monitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler
from app.repositories.optimization_repository import OptimizationRepository
from app.services.optimization_service import OptimizationService
from app.services.autonomy_service import AutonomyService
from app.repositories.llm_repository import LLMRepository
from app.services.llm_service import LLMService
from fastapi.staticfiles import StaticFiles
from app.services.chat_service import ChatService
from app.services.assistant_service import AssistantService
from app.core.autonomy.goal_manager import GoalManager

from app.core.agents.agent_manager import get_agent_manager
from app.core.workers.knowledge_consolidator import KnowledgeConsolidator
from app.core.workers.data_harvester import DataHarvester, MemoryConnector
from app.core.workers import data_harvester as data_harvester_module
from app.core.workers.neural_training_worker import start_neural_training_worker

setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializa a Infraestrutura de Baixo Nível
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

    # 2. Constrói o Grafo de Dependências (Composition Root)
    logger.info("Building and sharing dependency graph...")

    # --- Camada de Infraestrutura ---
    graph_db_instance = await get_graph_db()
    memory_db_instance = await get_memory_db()
    broker_instance = await get_broker()
    agent_manager_instance = get_agent_manager()

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
    # LLM (Sprint 10): Cérebro Híbrido
    app.state.llm_repo = LLMRepository()
    app.state.llm_service = LLMService(app.state.llm_repo)
    app.state.assistant_service = AssistantService(app.state.llm_service)

    try:
        warm_specs = getattr(settings, "LLM_POOL_WARM_PROVIDERS", []) or []
        if warm_specs:
            app.state.llm_service.warm_pool(warm_specs)
    except Exception:
        pass

    # Goals Manager (Autonomy)
    app.state.goal_manager = GoalManager(app.state.memory_service)

    # Chat: Conversas com histórico (MVP em memória)
    from app.repositories.chat_repository_sql import ChatRepositorySQL
    app.state.chat_repo = ChatRepositorySQL()
    app.state.chat_service = ChatService(app.state.chat_repo, app.state.llm_service, app.state.tool_service)

    # --- Self-Optimization (Sprint 7) ---
    app.state.optimization_repo = OptimizationRepository()
    app.state.optimization_service = OptimizationService(app.state.optimization_repo)

    # Autonomy Service (Loop contínuo)
    app.state.autonomy_service = AutonomyService(
        app.state.optimization_service,
        app.state.llm_service,
        app.state.goal_manager,
    )

    # Observabilidade: monitor e poison pill handler
    monitor = get_health_monitor()
    pp_handler = get_poison_pill_handler()
    app.state.observability_repo = ObservabilityRepository(monitor, pp_handler)
    app.state.observability_service = ObservabilityService(app.state.observability_repo)

    # Executa um check inicial e inicia monitoramento contínuo
    await monitor.check_all_components()
    await monitor.start_monitoring(interval_seconds=30)

    # 3. Instancia e Inicia os Workers com dependências injetadas
    logger.info("Initializing and starting background workers...")

    # Worker de Consolidação de Conhecimento
    knowledge_consolidator = KnowledgeConsolidator(
        agent_service=app.state.agent_service,
        memory_service=app.state.memory_service,
        knowledge_repo=app.state.knowledge_repo
    )

    # Worker de Coleta de Dados (Harvester)
    memory_connector = MemoryConnector(app.state.memory_repo)
    data_harvester = DataHarvester(connectors=[memory_connector])
    # Expõe instância no módulo para health check simples
    data_harvester_module.harvester = data_harvester

    # Inicia os workers
    await knowledge_consolidator.start()
    await data_harvester.start()
    # Inicia consumidor da fila de treinamento neural
    neural_training_task = await start_neural_training_worker()

    # Guarda referências para shutdown
    app.state.workers = [knowledge_consolidator, data_harvester]
    app.state.neural_training_consumer_task = neural_training_task

    logger.info("Application startup complete.")
    yield

    # === SHUTDOWN ===
    logger.info("Application shutdown: Closing resources...")
    for worker in app.state.workers:
        await worker.stop()

    # Cancela consumidor de treinamento
    try:
        if getattr(app.state, "neural_training_consumer_task", None):
            app.state.neural_training_consumer_task.cancel()
            # aguarda cancelamento
            with contextlib.suppress(asyncio.CancelledError):
                await app.state.neural_training_consumer_task
    except Exception:
        pass

    # Para o monitoramento contínuo de saúde antes de fechar recursos
    monitor.stop_monitoring()

    await asyncio.gather(close_graph_db(), close_memory_db(), close_broker())
    logger.info("Infrastructure connections closed.")
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect with a clean, decoupled architecture.",
    lifespan=lifespan
)
setup_tracing(app)

# --- Configuração da Aplicação ---
Instrumentator().instrument(app).expose(app)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ALLOW_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_exception_handlers(app)
 
# --- Autenticação por API Key (global) ---
# Se a variável de ambiente PUBLIC_API_KEY estiver definida, exige o header X-API-Key
API_KEY = getattr(settings, "PUBLIC_API_KEY", None)

if API_KEY:
    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        path = request.url.path
        skip_paths = ["/docs", "/openapi.json", "/redoc", "/healthz", "/metrics", "/static/"]
        if request.method == "OPTIONS" or any(path.startswith(p) for p in skip_paths):
            return await call_next(request)
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            logger.warning("Unauthorized request", path=path)
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

@app.middleware("http")
async def actor_binding(request: Request, call_next):
    try:
        request.state.actor_user_id = get_actor_user_id(request)
    except Exception:
        request.state.actor_user_id = None
    return await call_next(request)

app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def msgpack_content_negotiation(request: Request, call_next):
    accept = (request.headers.get("accept") or "").lower()
    response = await call_next(request)
    if "application/msgpack" in accept:
        ct = (response.headers.get("content-type") or "").lower()
        if ct.startswith("application/json"):
            try:
                body_bytes = getattr(response, "body", b"") or b""
                data = json.loads(body_bytes.decode("utf-8"))
                packed = msgpack.packb(data, use_bin_type=True)
                return Response(content=packed, media_type="application/msgpack")
            except Exception:
                return response
    return response

@app.get("/", include_in_schema=False)
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}

@app.get("/healthz", tags=["System"], summary="Health (basic)")
def healthz():
    return {"status": "ok"}

try:
    if getattr(settings, "SERVE_STATIC_FILES", False):
        app.mount(
            "/static",
            StaticFiles(directory=getattr(settings, "STATIC_FILES_DIR", "front/janus-angular/public"), check_dir=False),
            name="static",
        )

        @app.middleware("http")
        async def static_cache_control(request: Request, call_next):
            response = await call_next(request)
            path = request.url.path
            if path.startswith("/static/") and response.status_code == 200:
                try:
                    response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
                except Exception:
                    pass
            return response
except Exception:
    pass
