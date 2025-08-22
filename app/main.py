from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router
from app.db.graph import graph_db
import logging

logger = logging.getLogger(__name__)

# Lifespan events to manage resources like database connections
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("Application startup: Initializing resources...")
    # This will create the driver instance using the now-loaded settings
    graph_db.get_driver()
    yield
    # Code to run on shutdown
    logger.info("Application shutdown: Closing resources...")
    graph_db.close()

# Initialize the FastAPI application with the lifespan manager
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect.",
    lifespan=lifespan
)

# Include the API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    """Redirects to the API documentation."""
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}