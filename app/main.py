# app/main.py

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router
from app.db.graph import graph_db

# --- CONFIGURAÇÃO DE LOGGING ---
# MELHORIA: Adicionamos esta configuração para ter o máximo de logs.
# - level=logging.INFO: Diz para exibir mensagens INFO, WARNING, ERROR, e CRITICAL.
#   (Para ainda mais detalhes, poderíamos usar logging.DEBUG).
# - format: Define um formato claro para cada mensagem de log.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)

logger = logging.getLogger(__name__)


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

app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    """Redirects to the API documentation."""
    return {"message": f"Welcome to {settings.APP_PNAME}. Docs available at /docs"}