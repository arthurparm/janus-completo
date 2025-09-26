import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.config import settings
from app.core.correlation_middleware import CorrelationMiddleware
from app.core.logging_config import setup_logging
from app.core.meta_agent_cycle import run_meta_agent_cycle
from app.db.graph import graph_db

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing resources...")
    graph_db.get_driver()

    meta_agent_task = asyncio.create_task(run_meta_agent_cycle())

    yield

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
