# app/main.py
import asyncio  # <-- NOVA IMPORTAÇÃO
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator  # Mantenha a importação aqui

from app.api.v1.router import api_router
from app.config import settings
from app.core.correlation_middleware import CorrelationMiddleware
from app.core.logging_config import setup_logging
from app.core.meta_agent_cycle import run_meta_agent_cycle  # <-- NOVA IMPORTAÇÃO
from app.db.graph import graph_db

# Configura o logging estruturado para toda a aplicação
setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing resources...")
    graph_db.get_driver()

    # --- NOVA IMPLEMENTAÇÃO SPRINT 13: INICIAR O META-AGENTE ---
    # Inicia o ciclo do Meta-Agente como uma tarefa de fundo.
    # A tarefa continuará a ser executada enquanto a aplicação estiver ativa.
    meta_agent_task = asyncio.create_task(run_meta_agent_cycle())
    # --- FIM DA MODIFICAÇÃO ---
    
    yield
    
    # Quando a aplicação desliga, podemos cancelar a tarefa.
    meta_agent_task.cancel()
    logger.info("Application shutdown: Closing resources...")
    graph_db.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect.",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)

app.add_middleware(CorrelationMiddleware)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    """Redirects to the API documentation."""
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}