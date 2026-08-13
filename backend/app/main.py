import asyncio
import json
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Any

import msgpack
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    PROMETHEUS_INSTRUMENTATOR_AVAILABLE = True
except Exception:
    PROMETHEUS_INSTRUMENTATOR_AVAILABLE = False

    class Instrumentator:  # type: ignore[override]
        def instrument(self, _app: FastAPI):
            return self

        def expose(self, _app: FastAPI):
            return self

from app.api.exception_handlers import add_exception_handlers
from app.api.v1.router import api_router
from app.config import settings
from app.core.agents.graph_orchestrator import close_graph, init_graph
from app.core.bootstrap import bootstrap_dependencies
from app.core.infrastructure import (
    CorrelationMiddleware,
    DomainSLOMetricsMiddleware,
    RateLimitMiddleware,
    setup_logging,
    setup_tracing,
)
from app.core.kernel import Kernel, KernelState
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.monitoring import get_health_monitor
from app.core.security.autonomy_guard import validate_autonomous_evolution_disabled
from app.core.security.containment_middleware import SecurityContainmentMiddleware
from app.core.security.route_policy import (
    ApiProfile,
    configure_profile_routes,
    validate_route_policy,
)
from app.core.workers.orchestrator import get_orchestrator_worker_names, start_all_workers

# Determine log path
# Prefer escrever no volume montado /app/app dentro do container; fallback para cwd/janus.log
if os.path.isdir("/app/app"):
    log_file = "/app/app/janus.log"
else:
    log_file = os.path.join(os.getcwd(), "janus.log")

setup_logging(log_file=log_file)
logger = structlog.get_logger(__name__)
logger.debug("log_file_selected", log_file=log_file, cwd=os.getcwd())


def _cancel_tracked_worker_task(task: Any) -> int:
    if isinstance(task, (list, tuple)):
        return sum(_cancel_tracked_worker_task(child) for child in task)
    if isinstance(task, asyncio.Task) and not task.cancelled():
        task.cancel()
        return 1
    return 0


def cancel_tracked_orchestrator_workers(raw_workers: Any) -> int:
    if not isinstance(raw_workers, list):
        logger.warning(
            "shutdown_invalid_workers_collection",
            collection_type=type(raw_workers).__name__,
        )
        return 0

    cancelled = 0
    for index, worker in enumerate(raw_workers):
        if not isinstance(worker, Mapping):
            logger.warning(
                "shutdown_invalid_worker_item",
                index=index,
                item_type=type(worker).__name__,
            )
            continue

        task = worker.get("task")
        cancelled += _cancel_tracked_worker_task(task)
    return cancelled


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_route_policy(app)
    validate_autonomous_evolution_disabled(app)

    profile = ApiProfile(settings.JANUS_API_PROFILE)
    if profile is ApiProfile.PUBLIC or settings.JANUS_SKIP_EXTERNAL_STARTUP:
        logger.info("external_startup_skipped", api_profile=profile.value)
        yield
        return

    # 0.5 Validate critical secrets in production before bootstrapping services.
    from app.core.security.secret_validator import validate_production_secrets

    validate_production_secrets()

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

    # 1.0 Initialize LangGraph orchestrator/checkpointer lifecycle
    await init_graph()

    # 1.1 Load Global Prompts (Async)
    # This ensures that all prompt constants are populated from the DB before the app starts serving requests.
    from app.core.evolution.prompts import load_evolution_prompts
    from app.core.infrastructure.advanced_prompts import load_advanced_prompts
    from app.core.infrastructure.janus_specialized_prompts import load_specialized_prompts

    logger.info("Loading global prompts from database...")
    try:
        await load_advanced_prompts()
        await load_specialized_prompts()
        await load_evolution_prompts()
        logger.info("Global prompts loaded successfully.")
    except Exception as e:
        logger.error("log_error", message=f"Failed to load global prompts: {e}")
        # We don't raise here to allow startup with empty prompts (they might be fetched on demand or fallback)

    await bootstrap_dependencies(app)
    try:
        from app.services.autonomy_admin_service import AutonomyAdminService

        app.state.autonomy_admin_service = AutonomyAdminService(
            llm_service=kernel.llm_service,
            knowledge_service=kernel.knowledge_service,
            goal_manager=kernel.goal_manager,
        )
    except Exception as e:
        logger.warning("autonomy_admin_service_init_failed", error=str(e), exc_info=e)

    # 3. Initialize Rate Limits
    from app.core.llm.rate_limiter import configure_rate_limits_from_settings

    if hasattr(settings, "LLM_RATE_LIMITS") and settings.LLM_RATE_LIMITS:
        configure_rate_limits_from_settings(
            settings.LLM_RATE_LIMITS, getattr(settings, "LLM_RATE_LIMIT_THRESHOLD", 0.80)
        )
        logger.info("LLM Rate Limits initialized.")

    # 4.5 Start orchestrator-managed workers (queue consumers) if enabled.
    if (
        profile in {ApiProfile.CONTROL_PLANE, ApiProfile.ALL_TEST}
        and getattr(settings, "START_ORCHESTRATOR_WORKERS_ON_STARTUP", False)
    ):
        try:
            current = getattr(app.state, "orchestrator_workers", []) or []
            if not current:
                workers = await start_all_workers()
                names = get_orchestrator_worker_names()
                payload = []
                for idx, task in enumerate(workers):
                    name = names[idx] if idx < len(names) else f"worker_{idx}"
                    payload.append({"name": name, "task": task})
                app.state.orchestrator_workers = payload
                logger.info("Orchestrator workers started on startup.", count=len(payload))
        except Exception as e:
            logger.error("Failed to start orchestrator workers on startup.", exc_info=e)

    # 4.6 Startup self-study health check (non-blocking)
    try:
        service = getattr(app.state, "autonomy_admin_service", None)
        if service is not None:
            async def _startup_self_study_wrapper():
                try:
                    outcome = await service.startup_self_study_check()
                    logger.info("startup_self_study_check_completed", outcome=outcome)
                except Exception as inner:
                    logger.warning("startup_self_study_check_failed", error=str(inner), exc_info=inner)

            asyncio.create_task(_startup_self_study_wrapper())
    except Exception as e:
        logger.warning("startup_self_study_check_schedule_failed", error=str(e), exc_info=e)

    yield

    # === SHUTDOWN ===
    try:
        current = getattr(app.state, "orchestrator_workers", []) or []
        cancel_tracked_orchestrator_workers(current)
    except Exception as e:
        logger.warning("Failed to stop orchestrator workers on shutdown.", exc_info=e)
    await asyncio.shield(close_graph())
    await asyncio.shield(kernel.shutdown())
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: An autonomous, modular AI software architect with a clean, decoupled architecture.",
    lifespan=lifespan,
    # Routes always registered; SecurityContainmentMiddleware blocks them in non-development.
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

if PROMETHEUS_INSTRUMENTATOR_AVAILABLE:
    Instrumentator().instrument(app)
else:
    logger.warning(
        "prometheus_instrumentator_unavailable",
        detail=(
            "prometheus_fastapi_instrumentator not installed in this Python environment. "
            "Running without HTTP metrics instrumentation."
        ),
    )
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(DomainSLOMetricsMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ALLOW_ORIGINS", []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityContainmentMiddleware)
add_exception_handlers(app)

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


def _get_dependency_health() -> dict[str, Any]:
    try:
        kernel = Kernel.get_instance()
        monitor = get_health_monitor()
        kernel_state = kernel.state
        degraded_dependencies = kernel.degraded_dependencies

        checks = {}
        if monitor:
            for component in getattr(monitor, "health_checks", {}).keys():
                checks[component] = {
                    "status": "unknown",
                    "duration_seconds": 0.0,
                    "checked_at": None,
                    "error": "Health check has not reported yet",
                }
            for component, result in getattr(monitor, "last_results", {}).items():
                checks[component] = {
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "duration_seconds": result.duration_seconds,
                    "checked_at": result.checked_at.isoformat() if hasattr(result.checked_at, 'isoformat') else str(result.checked_at),
                    "error": result.error,
                }

        return {
            "kernel_state": kernel_state,
            "degraded_dependencies": degraded_dependencies,
            "checks": checks,
        }
    except Exception:
        return {
            "kernel_state": "unknown",
            "degraded_dependencies": {},
            "checks": {},
        }


@app.get(
    "/healthz/public",
    tags=["System"],
    summary="Public liveness",
    operation_id="get_public_liveness",
)
def healthz_public():
    return {"status": "ok", "profile": "public"}


@app.get(
    "/healthz/user",
    tags=["System"],
    summary="User API liveness",
    operation_id="get_user_liveness",
)
def healthz_user():
    deps = _get_dependency_health()
    return {
        "status": "ok",
        "profile": "user",
        "dependencies": deps,
    }


@app.get(
    "/healthz/control-plane",
    tags=["System"],
    summary="Control-plane liveness",
    operation_id="get_control_plane_liveness",
)
def healthz_control_plane():
    return {"status": "ok", "profile": "control-plane"}


@app.get(
    "/health",
    tags=["System"],
    summary="Health (detailed)",
    operation_id="get_control_plane_health",
)
def health():
    build_ref = str(os.getenv("JANUS_BUILD_REF") or "").strip() or None
    deps = _get_dependency_health()
    kernel_state = deps["kernel_state"]
    has_checks = bool(deps["checks"])

    if not has_checks:
        top_status = kernel_state
    else:
        critical_failure = False
        critical_degraded = False
        non_critical_failure = False

        try:
            monitor = get_health_monitor()
            for component, check in deps["checks"].items():
                is_critical = False
                try:
                    is_critical = monitor.health_checks.get(component, {}).get("is_critical", False)
                except Exception:
                    pass

                check_status = str(check.get("status", "unknown"))
                if check_status != "healthy":
                    if is_critical:
                        if check_status == "unhealthy":
                            critical_failure = True
                        else:
                            critical_degraded = True
                    else:
                        non_critical_failure = True
        except Exception:
            pass

        if kernel_state == KernelState.CRITICAL or critical_failure:
            top_status = "critical"
        elif kernel_state == KernelState.DEGRADED or critical_degraded or non_critical_failure:
            top_status = "degraded"
        else:
            top_status = "healthy"

    health_info = {
        "status": top_status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "kernel_state": kernel_state,
        "degraded_dependencies": deps["degraded_dependencies"],
        "dependencies": deps["checks"],
        "tailscale": {
            "enabled": settings.TAILSCALE_SERVE_ENABLED,
            "host": settings.TAILSCALE_HOST,
            "backend_url": settings.TAILSCALE_BACKEND_URL,
            "frontend_url": settings.TAILSCALE_FRONTEND_URL,
        }
        if settings.TAILSCALE_SERVE_ENABLED
        else None,
    }
    if build_ref:
        health_info["build_ref"] = build_ref
    return health_info


@app.get(
    "/metrics",
    tags=["System"],
    operation_id="get_prometheus_metrics",
)
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


try:
    if getattr(settings, "SERVE_STATIC_FILES", False):
        app.mount(
            "/static",
            StaticFiles(
                directory=getattr(settings, "STATIC_FILES_DIR", "frontend/dist/janus-angular/browser"),
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


app.state.api_profile = ApiProfile(settings.JANUS_API_PROFILE)
app.state.route_policy_matrix = configure_profile_routes(app, app.state.api_profile)


def _profile_openapi() -> dict[str, Any]:
    if app.openapi_schema is not None:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schemes["OIDCUser"] = {
        "type": "openIdConnect",
        "openIdConnectUrl": settings.OIDC_ISSUER.rstrip("/")
        + "/.well-known/openid-configuration",
    }
    control_scopes = sorted(
        {
            scope
            for policy in app.state.route_policy_matrix
            if policy.profile is ApiProfile.CONTROL_PLANE
            for scope in policy.scopes
        }
    )
    schemes["OIDCService"] = {
        "type": "oauth2",
        "flows": {
            "clientCredentials": {
                "tokenUrl": settings.OIDC_SERVICE_TOKEN_URL or "https://idp.invalid/token",
                "scopes": {scope: scope for scope in control_scopes},
            }
        },
    }
    admin_action = (
        schema.get("paths", {})
        .get("/api/v1/admin-actions", {})
        .get("post")
    )
    if admin_action is not None:
        delegable = sorted(
            policy.operation_id
            for policy in app.state.route_policy_matrix
            if policy.profile is ApiProfile.CONTROL_PLANE and policy.human_delegable
        )
        variants = [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["operation_id"],
                "properties": {
                    "operation_id": {"type": "string", "const": operation_id},
                    "path_params": {
                        "type": "object",
                        "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                        "default": {},
                    },
                    "query_params": {
                        "type": "object",
                        "additionalProperties": True,
                        "default": {},
                    },
                    "payload": {"type": "object", "default": {}},
                },
            }
            for operation_id in delegable
        ]
        admin_action["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": variants,
                        "discriminator": {"propertyName": "operation_id"},
                    }
                }
            },
        }
        admin_action["x-janus-delegable-operation-ids"] = delegable
    schema["x-janus-api-profile"] = app.state.api_profile.value
    app.openapi_schema = schema
    return schema


app.openapi = _profile_openapi  # type: ignore[method-assign]
