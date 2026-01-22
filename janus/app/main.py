import json
import os
from contextlib import asynccontextmanager

import msgpack
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.exception_handlers import add_exception_handlers
from app.api.v1.router import api_router
from app.config import settings
from app.core.infrastructure import (
    CorrelationMiddleware,
    RateLimitMiddleware,
    setup_logging,
    setup_tracing,
)
from app.core.infrastructure.auth import get_actor_user_id
from app.core.kernel import Kernel
from app.core.middleware.security_headers import SecurityHeadersMiddleware

# Determine log path
# Prefer escrever no volume montado /app/app dentro do container; fallback para cwd/janus.log
if os.path.isdir("/app/app"):
    log_file = "/app/app/janus.log"
else:
    log_file = os.path.join(os.getcwd(), "janus.log")

print(f"[DEBUG_INIT] Log file selected: {log_file} (CWD: {os.getcwd()})")
setup_logging(log_file=log_file)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. Validate LangSmith Configuration
    if settings.LANGCHAIN_TRACING_V2 == "true":
        if not settings.LANGCHAIN_API_KEY:
            logger.warning(
                "LangSmith tracing is enabled (LANGCHAIN_TRACING_V2=true) but LANGCHAIN_API_KEY is missing. "
                "Tracing may fail or be ignored."
            )
        else:
            logger.info("LangSmith tracing enabled and API key configured.")

    # 1. Initialize Kernel (Infrastructure & Dependencies)
    kernel = Kernel.get_instance()
    await kernel.startup()

    # 1.1 Load Global Prompts (Async)
    # This ensures that all prompt constants are populated from the DB before the app starts serving requests.
    from app.core.infrastructure.advanced_prompts import load_advanced_prompts
    from app.core.infrastructure.janus_specialized_prompts import load_specialized_prompts
    from app.core.evolution.prompts import load_evolution_prompts
    
    logger.info("Loading global prompts from database...")
    try:
        await load_advanced_prompts()
        await load_specialized_prompts()
        await load_evolution_prompts()
        logger.info("Global prompts loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load global prompts: {e}")
        # We don't raise here to allow startup with empty prompts (they might be fetched on demand or fallback)

    # 2. Map Kernel Services to App State (for backward compatibility with Routers)
    app.state.graph_db = kernel.graph_db
    app.state.memory_db = kernel.memory_db
    app.state.broker = kernel.broker
    app.state.agent_manager = kernel.agent_manager

    app.state.agent_service = kernel.agent_service
    app.state.memory_service = kernel.memory_service
    app.state.knowledge_service = kernel.knowledge_service
    app.state.task_service = kernel.task_service
    app.state.context_service = kernel.context_service
    app.state.sandbox_service = kernel.sandbox_service
    app.state.reflexion_service = kernel.reflexion_service
    app.state.tool_service = kernel.tool_service
    app.state.collaboration_service = kernel.collaboration_service
    app.state.document_service = kernel.document_service
    app.state.observability_service = kernel.observability_service
    app.state.optimization_service = kernel.optimization_service
    app.state.autonomy_service = kernel.autonomy_service
    app.state.llm_service = kernel.llm_service
    app.state.chat_service = kernel.chat_service
    app.state.assistant_service = kernel.assistant_service
    app.state.goal_manager = kernel.goal_manager

    # Store workers in app state if needed by old shutdown logic, but we use kernel.shutdown now
    app.state.workers = kernel.workers

    # 3. Initialize Rate Limits
    from app.core.llm.rate_limiter import configure_rate_limits_from_settings

    if hasattr(settings, "LLM_RATE_LIMITS") and settings.LLM_RATE_LIMITS:
        configure_rate_limits_from_settings(
            settings.LLM_RATE_LIMITS, getattr(settings, "LLM_RATE_LIMIT_THRESHOLD", 0.80)
        )
        logger.info("LLM Rate Limits initialized.")

    # 4. Initialize Firebase (Persistence) - MOVED TO KERNEL
    # Removed from here to avoid race condition with GoalManager
    pass

    yield

    # === SHUTDOWN ===
    await kernel.shutdown()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect with a clean, decoupled architecture.",
    lifespan=lifespan,
)
setup_tracing(app)

# --- Configuração da Aplicação ---
Instrumentator().instrument(app).expose(app)
app.add_middleware(SecurityHeadersMiddleware)
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


@app.get("/health", tags=["System"], summary="Health (detailed)")
def health():
    """Health check detalhado com informações do sistema"""
    health_info = {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "tailscale": {
            "enabled": settings.TAILSCALE_SERVE_ENABLED,
            "host": settings.TAILSCALE_HOST,
            "backend_url": settings.TAILSCALE_BACKEND_URL,
            "frontend_url": settings.TAILSCALE_FRONTEND_URL,
        }
        if settings.TAILSCALE_SERVE_ENABLED
        else None,
    }
    return health_info


try:
    if getattr(settings, "SERVE_STATIC_FILES", False):
        app.mount(
            "/static",
            StaticFiles(
                directory=getattr(settings, "STATIC_FILES_DIR", "front/janus-angular/public"),
                check_dir=False,
            ),
            name="static",
        )

        @app.middleware("http")
        async def static_cache_control(request: Request, call_next):
            response = await call_next(request)
            path = request.url.path
            if path.startswith("/static/") and response.status_code == 200:
                try:
                    response.headers.setdefault(
                        "Cache-Control", "public, max-age=31536000, immutable"
                    )
                except Exception:
                    pass
            return response
except Exception:
    pass
