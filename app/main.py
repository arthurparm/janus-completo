import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.exception_handlers import add_exception_handlers
from app.api.v1.router import api_router
from app.config import settings

# Importa os inicializadores de infraestrutura
from app.core.infrastructure import (
    CorrelationMiddleware, RateLimitMiddleware, setup_logging,
    initialize_broker, close_broker, get_broker
)
from app.db.graph import initialize_graph_db, close_graph_db, get_graph_db
from app.core.memory.memory_core import initialize_memory_db, close_memory_db, get_memory_db

# Importa as classes e getters para a construção do grafo de dependências
from app.repositories import *  # Importa todos os repositórios
from app.services import *  # Importa todos os serviços
from app.core.agents.agent_manager import get_agent_manager
from app.core.workers.knowledge_consolidator import KnowledgeConsolidator
from app.core.workers.data_harvester import DataHarvester, MemoryConnector

setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializa a Infraestrutura de Baixo Nível
    logger.info("Application startup: Initializing infrastructure...")
    try:
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
    # Adicione outros getters de infraestrutura aqui...

    # --- Camada de Repositório ---
    app.state.knowledge_repo = KnowledgeRepository(graph_db_instance)
    app.state.memory_repo = MemoryRepository(memory_db_instance)
    app.state.agent_repo = AgentRepository(agent_manager_instance)
    app.state.task_repo = TaskRepository(broker_instance)
    # Adicione outros repositórios aqui...

    # --- Camada de Serviço ---
    app.state.agent_service = AgentService(app.state.agent_repo)
    app.state.memory_service = MemoryService(app.state.memory_repo)
    app.state.knowledge_service = KnowledgeService(app.state.knowledge_repo)
    app.state.task_service = TaskService(app.state.task_repo)
    # Adicione outros serviços aqui...

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

    # Inicia os workers
    await knowledge_consolidator.start()
    await data_harvester.start()
    app.state.workers = [knowledge_consolidator, data_harvester]

    logger.info("Application startup complete.")
    yield

    # === SHUTDOWN ===
    logger.info("Application shutdown: Closing resources...")
    for worker in app.state.workers:
        await worker.stop()

    await asyncio.gather(close_graph_db(), close_memory_db(), close_broker())
    logger.info("Infrastructure connections closed.")
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect with a clean, decoupled architecture.",
    lifespan=lifespan
)

# --- Configuração da Aplicação ---
Instrumentator().instrument(app).expose(app)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)
add_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}

@app.get("/healthz", tags=["System"], summary="Health (basic)")
def healthz():
    return {"status": "ok"}
