# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router
from app.db.graph import graph_db

# Nossas novas importações
from app.core.logging_config import setup_logging
from app.core.correlation_middleware import CorrelationMiddleware
import structlog

# Configura o logging estruturado para toda a aplicação
setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing resources...")
    graph_db.get_driver()
    yield
    logger.info("Application shutdown: Closing resources...")
    graph_db.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect.",
    lifespan=lifespan
)

app.add_middleware(CorrelationMiddleware)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    """Redirects to the API documentation."""
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}