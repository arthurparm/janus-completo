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

# Constantes
_HEALTH_CHECK_TIMEOUT = 5  # segundos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação (startup/shutdown).

    Inclui inicialização de conexões, tasks em background e cleanup graceful.
    """
    # Banner
    logger.info({
        "event": "startup_banner",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENVIRONMENT,
    })

    logger.info("Application startup: Initializing resources...")

    # Initialize DB connections (Neo4j)
    try:
        driver = graph_db.get_driver()
        logger.info("Neo4j driver inicializado com sucesso.")
    except Exception as e:
        logger.error(
            f"Falha ao inicializar driver Neo4j: {e}. "
            f"Funcionalidades de grafo estarão indisponíveis.",
            exc_info=True
        )

    # Start meta agent cycle
    meta_agent_task = None
    try:
        meta_agent_task = asyncio.create_task(run_meta_agent_cycle())
        logger.info("Meta-agente cycle iniciado.")
    except Exception as e:
        logger.error(f"Falha ao iniciar meta-agente cycle: {e}", exc_info=True)

    # Start data harvester
    try:
        await harvester.start()
        logger.info("Data harvester iniciado.")
    except Exception as e:
        logger.warning(f"Harvester failed to start: {e}. Continuando sem ele.", exc_info=True)

    logger.info("Application startup complete.")

    yield

    # === SHUTDOWN ===
    logger.info("Application shutdown: Closing resources...")

    # Stop meta agent cycle
    if meta_agent_task and not meta_agent_task.done():
        meta_agent_task.cancel()
        try:
            await asyncio.wait_for(meta_agent_task, timeout=10)
            logger.info("Meta-agente cycle encerrado gracefully.")
        except asyncio.TimeoutError:
            logger.warning("Meta-agente cycle não encerrou no tempo esperado.")
        except asyncio.CancelledError:
            logger.info("Meta-agente cycle cancelado.")
        except Exception as e:
            logger.error(f"Erro ao encerrar meta-agente cycle: {e}", exc_info=True)

    # Stop data harvester
    try:
        await asyncio.wait_for(harvester.stop(), timeout=10)
        logger.info("Data harvester encerrado gracefully.")
    except asyncio.TimeoutError:
        logger.warning("Data harvester não encerrou no tempo esperado.")
    except Exception as e:
        logger.error(f"Erro ao encerrar harvester: {e}", exc_info=True)

    # Close Neo4j
    try:
        graph_db.close()
        logger.info("Neo4j driver fechado.")
    except Exception as e:
        logger.error(f"Erro ao fechar Neo4j driver: {e}", exc_info=True)

    logger.info("Application shutdown complete.")


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
    """Endpoint raiz com link para documentação."""
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}


@app.get("/healthz", tags=["System"], summary="Health (basic)")
def healthz():
    """
    Health check básico.

    Retorna sucesso se a aplicação está rodando.
    """
    return {"status": "ok", "name": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/livez", tags=["System"], summary="Liveness")
def livez():
    """
    Liveness probe para Kubernetes.

    Indica se a aplicação está viva (não travada).
    """
    return {"alive": True}


@app.get("/readyz", tags=["System"], summary="Readiness")
async def readyz():
    """
    Readiness probe para Kubernetes.

    Verifica se a aplicação está pronta para receber tráfego,
    incluindo dependências críticas (Neo4j, Qdrant).
    """
    # Neo4j
    neo4j_ok = False
    neo4j_error = None
    try:
        neo4j_ok = await asyncio.wait_for(
            asyncio.to_thread(graph_db.health_check),
            timeout=_HEALTH_CHECK_TIMEOUT
        )
    except asyncio.TimeoutError:
        neo4j_error = "timeout"
        logger.warning(f"Neo4j health check timeout após {_HEALTH_CHECK_TIMEOUT}s")
    except Exception as e:
        neo4j_error = str(e)
        logger.warning(f"Neo4j health check falhou: {e}")

    # Qdrant
    qdrant_ok = False
    qdrant_error = None
    try:
        qdrant_ok = await asyncio.wait_for(
            asyncio.to_thread(check_qdrant_readiness),
            timeout=_HEALTH_CHECK_TIMEOUT
        )
    except asyncio.TimeoutError:
        qdrant_error = "timeout"
        logger.warning(f"Qdrant health check timeout após {_HEALTH_CHECK_TIMEOUT}s")
    except Exception as e:
        qdrant_error = str(e)
        logger.warning(f"Qdrant health check falhou: {e}")

    # LLM (best-effort - não bloqueia readiness)
    llm_ok = False
    llm_error = None
    try:
        client = get_llm_client(role=ModelRole.ORCHESTRATOR)
        llm_ok = await asyncio.wait_for(
            asyncio.to_thread(client.health_check),
            timeout=_HEALTH_CHECK_TIMEOUT
        )
    except asyncio.TimeoutError:
        llm_error = "timeout"
        logger.warning(f"LLM health check timeout após {_HEALTH_CHECK_TIMEOUT}s")
    except Exception as e:
        llm_error = str(e)
        logger.warning(f"LLM health check falhou: {e}")

    # Ready se dependências críticas estiverem OK
    ready = bool(neo4j_ok and qdrant_ok)

    response = {
        "ready": ready,
        "dependencies": {
            "neo4j": {
                "status": "healthy" if neo4j_ok else "unhealthy",
                "error": neo4j_error
            },
            "qdrant": {
                "status": "healthy" if qdrant_ok else "unhealthy",
                "error": qdrant_error
            },
            "llm": {
                "status": "healthy" if llm_ok else "unhealthy",
                "error": llm_error
            },
        }
    }

    return response
