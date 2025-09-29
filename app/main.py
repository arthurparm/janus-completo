import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.api.problem_details import add_problem_handlers
from app.config import settings
from app.core.correlation_middleware import CorrelationMiddleware
from app.core.rate_limit_middleware import RateLimitMiddleware
from app.core.logging_config import setup_logging
from app.core.meta_agent_cycle import run_meta_agent_cycle
from app.db.graph import graph_db
from app.db.vector_store import check_qdrant_readiness
from app.core.llm_manager import get_llm_client, ModelRole
from app.core.data_harvester import harvester

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Banner
    logger.info({
        "event": "startup_banner",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENVIRONMENT,
    })

    logger.info("Application startup: Initializing resources...")
    # Initialize DB connections (Neo4j)
    graph_db.get_driver()

    # Start meta agent cycle
    meta_agent_task = asyncio.create_task(run_meta_agent_cycle())
    # Start data harvester
    try:
        await harvester.start()
    except Exception:
        logger.warning("Harvester failed to start; continuing without it.")

    yield

    meta_agent_task.cancel()
    # Stop data harvester
    try:
        await harvester.stop()
    except Exception:
        pass
    logger.info("Application shutdown: Closing resources...")
    graph_db.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect.",
    lifespan=lifespan
)

# Metrics
Instrumentator().instrument(app).expose(app)

# Middlewares
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)

# Problem Details error handlers
add_problem_handlers(app)

# Routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}


@app.get("/healthz", tags=["System"], summary="Health (basic)")
def healthz():
    return {"status": "ok", "name": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/livez", tags=["System"], summary="Liveness")
def livez():
    return {"alive": True}


@app.get("/readyz", tags=["System"], summary="Readiness")
def readyz():
    # Neo4j
    neo4j_ok = False
    try:
        neo4j_ok = graph_db.health_check()
    except Exception:
        neo4j_ok = False
    # Qdrant
    qdrant_ok = False
    try:
        qdrant_ok = check_qdrant_readiness()
    except Exception:
        qdrant_ok = False
    # LLM (best-effort)
    llm_ok = False
    try:
        llm_ok = get_llm_client(role=ModelRole.ORCHESTRATOR).health_check()
    except Exception:
        llm_ok = False

    ready = bool(neo4j_ok and qdrant_ok)
    return {
        "ready": ready,
        "dependencies": {
            "neo4j": neo4j_ok,
            "qdrant": qdrant_ok,
            "llm": llm_ok,
        }
    }
