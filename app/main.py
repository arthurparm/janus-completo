import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.problem_details import add_problem_handlers
from app.api.v1.router import api_router
from app.config import settings
from app.core.agents import run_meta_agent_cycle
from app.core.infrastructure import CorrelationMiddleware, RateLimitMiddleware, setup_logging
from app.core.memory import initialize_memory_core
from app.core.workers import harvester
from app.db.graph import graph_db
from app.db.vector_store import check_qdrant_readiness

setup_logging()
logger = structlog.get_logger(__name__)

# Constantes
_HEALTH_CHECK_TIMEOUT = 10  # segundos


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info({
        "event": "startup_banner",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENVIRONMENT,
    })
    logger.info("Application startup: Initializing resources...")

    # Inicializa o Memory Core de forma assíncrona
    try:
        await asyncio.wait_for(initialize_memory_core(), timeout=30)
        logger.info("Memory Core inicializado com sucesso.")
    except asyncio.TimeoutError:
        logger.error("Timeout ao inicializar Memory Core. Algumas funcionalidades podem ser afetadas.")
    except Exception as e:
        logger.error(f"Falha ao inicializar Memory Core: {e}", exc_info=True)

    # Conexões com DB (Neo4j)
    try:
        graph_db.get_driver()
        logger.info("Neo4j driver inicializado.")
    except Exception as e:
        logger.error(f"Falha ao inicializar driver Neo4j: {e}", exc_info=True)

    # Tasks em background
    meta_agent_task = asyncio.create_task(run_meta_agent_cycle())
    logger.info("Meta-agente cycle iniciado.")
    await harvester.start()
    logger.info("Data harvester iniciado.")

    logger.info("Application startup complete.")
    yield

    # === SHUTDOWN ===
    logger.info("Application shutdown: Closing resources...")
    if meta_agent_task and not meta_agent_task.done():
        meta_agent_task.cancel()
        try:
            await meta_agent_task
        except asyncio.CancelledError:
            logger.info("Meta-agente cycle cancelado.")
    await harvester.stop()
    graph_db.close()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect.",
    lifespan=lifespan
)

# Middlewares e Rotas
Instrumentator().instrument(app).expose(app)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)
add_problem_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}


@app.get("/healthz", tags=["System"], summary="Health (basic)")
def healthz():
    return {"status": "ok"}


@app.get("/livez", tags=["System"], summary="Liveness")
def livez():
    return {"alive": True}


@app.get("/readyz", tags=["System"], summary="Readiness")
async def readyz():
    """Verifica se a aplicação e suas dependências críticas estão prontas."""
    deps = await asyncio.gather(
        graph_db.ahealth_check(),
        check_qdrant_readiness(),
        # Adicione outros checks assíncronos aqui
        return_exceptions=True
    )
    neo4j_ok, qdrant_ok = [isinstance(res, bool) and res for res in deps]

    return {
        "ready": neo4j_ok and qdrant_ok,
        "dependencies": {
            "neo4j": {"status": "healthy" if neo4j_ok else "unhealthy",
                      "error": str(deps[0]) if not neo4j_ok else None},
            "qdrant": {"status": "healthy" if qdrant_ok else "unhealthy",
                       "error": str(deps[1]) if not qdrant_ok else None},
        }
    }
