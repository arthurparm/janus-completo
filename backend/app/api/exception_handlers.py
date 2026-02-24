import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

# Importa as excecoes customizadas de cada servico
from app.services.agent_service import AgentServiceError, AgentTimeoutError
from app.services.collaboration_service import (
    AgentNotFoundError,
    CollaborationServiceError,
    TaskNotFoundError,
)
from app.services.context_service import ContextServiceError
from app.services.knowledge_service import KnowledgeServiceError
from app.services.learning_service import (
    LearningServiceError,
    ModelNotFoundError,
    TrainingFailedError,
)
from app.services.llm_service import LLMServiceError, LLMTimeoutError
from app.services.memory_service import MemoryServiceError

try:
    from app.services.meta_agent_service import MetaAgentServiceError
except Exception:

    class MetaAgentServiceError(Exception):  # type: ignore
        pass


from app.services.observability_service import MessageNotFoundError, ObservabilityServiceError
from app.services.optimization_service import OptimizationServiceError
from app.services.sandbox_service import InvalidInputError, SandboxError
from app.services.task_service import TaskServiceError
from app.services.tool_service import (
    ProtectedToolError,
    ToolCreationError,
    ToolNotFoundError,
    ToolServiceError,
)

logger = structlog.get_logger(__name__)

_ERROR_TAXONOMY: dict[str, dict[str, str | int]] = {
    "RESOURCE_NOT_FOUND": {
        "category": "not_found",
        "http_status": status.HTTP_404_NOT_FOUND,
        "description": "Requested resource does not exist.",
    },
    "INVALID_INPUT": {
        "category": "validation",
        "http_status": status.HTTP_400_BAD_REQUEST,
        "description": "Request payload or parameters are invalid.",
    },
    "SERVICE_TIMEOUT": {
        "category": "timeout",
        "http_status": status.HTTP_408_REQUEST_TIMEOUT,
        "description": "Service operation timed out.",
    },
    "ACCESS_DENIED": {
        "category": "authz",
        "http_status": status.HTTP_403_FORBIDDEN,
        "description": "Access denied by authorization policy.",
    },
    "INTERNAL_SERVICE_ERROR": {
        "category": "internal",
        "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "description": "Unexpected internal service failure.",
    },
}

# --- Mapeamento de Excecoes para Status HTTP ---

# Excecoes que indicam que um recurso nao foi encontrado (404)
NOT_FOUND_EXCEPTIONS = (
    AgentNotFoundError,
    TaskNotFoundError,
    ModelNotFoundError,
    MessageNotFoundError,
    ToolNotFoundError,
)

# Excecoes que indicam uma entrada invalida do cliente (400)
BAD_REQUEST_EXCEPTIONS = (
    InvalidInputError,
    ProtectedToolError,
    ToolCreationError,
    TrainingFailedError,
    ValueError,  # Captura erros de validacao de enum, etc.
)

# Excecoes que indicam timeout (408)
TIMEOUT_EXCEPTIONS = (
    AgentTimeoutError,
    LLMTimeoutError,
)


def get_error_taxonomy_catalog() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for code, data in _ERROR_TAXONOMY.items():
        rows.append({"error_code": code, **data})
    return rows


def _error_payload(
    request: Request,
    *,
    status_code: int,
    detail: str,
    error_code: str,
) -> dict:
    taxonomy = _ERROR_TAXONOMY.get(error_code, _ERROR_TAXONOMY["INTERNAL_SERVICE_ERROR"])
    trace_id = getattr(request.state, "correlation_id", None)
    return {
        "detail": detail,
        "error_code": error_code,
        "error_category": taxonomy.get("category"),
        "status": status_code,
        "trace_id": trace_id,
    }


# --- Handlers Genericos ---


async def http_404_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning(
        "resource_not_found",
        url=request.url.path,
        exception_type=type(exc).__name__,
        detail=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=_error_payload(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            error_code="RESOURCE_NOT_FOUND",
        ),
    )


async def http_400_bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = str(exc)
    error_code = "ACCESS_DENIED" if "access denied" in detail.lower() else "INVALID_INPUT"
    status_code = (
        status.HTTP_403_FORBIDDEN if error_code == "ACCESS_DENIED" else status.HTTP_400_BAD_REQUEST
    )
    logger.warning(
        "access_denied" if error_code == "ACCESS_DENIED" else "request_invalid",
        url=request.url.path,
        detail=detail,
        error_code=error_code,
    )
    return JSONResponse(
        status_code=status_code,
        content=_error_payload(
            request,
            status_code=status_code,
            detail=detail,
            error_code=error_code,
        ),
    )


async def http_408_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("service_operation_timeout", exc_info=exc, url=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content=_error_payload(
            request,
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=str(exc),
            error_code="SERVICE_TIMEOUT",
        ),
    )


async def generic_service_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("service_unexpected_error", exc_info=exc, url=request.url.path)
    detail = str(exc)
    error_code = "ACCESS_DENIED" if "access denied" in detail.lower() else "INTERNAL_SERVICE_ERROR"
    status_code = (
        status.HTTP_403_FORBIDDEN
        if error_code == "ACCESS_DENIED"
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    return JSONResponse(
        status_code=status_code,
        content=_error_payload(
            request,
            status_code=status_code,
            detail=f"Ocorreu um erro interno no servico: {detail}",
            error_code=error_code,
        ),
    )


# --- Funcao para registrar todos os handlers ---


def add_exception_handlers(app):
    """Adiciona todos os manipuladores de excecao customizados a aplicacao FastAPI."""
    logger.info("Registrando manipuladores de excecao customizados.")

    exception_map = {
        **{exc: http_404_not_found_handler for exc in NOT_FOUND_EXCEPTIONS},
        **{exc: http_400_bad_request_handler for exc in BAD_REQUEST_EXCEPTIONS},
        **{exc: http_408_timeout_handler for exc in TIMEOUT_EXCEPTIONS},
    }

    for exc_type, handler in exception_map.items():
        app.add_exception_handler(exc_type, handler)

    # Handler generico para todas as outras excecoes de servico
    all_service_exceptions = (
        AgentServiceError,
        CollaborationServiceError,
        ContextServiceError,
        KnowledgeServiceError,
        LearningServiceError,
        LLMServiceError,
        MemoryServiceError,
        MetaAgentServiceError,
        ObservabilityServiceError,
        OptimizationServiceError,
        SandboxError,
        TaskServiceError,
        ToolServiceError,
    )
    for exc_type in all_service_exceptions:
        if exc_type not in exception_map:
            app.add_exception_handler(exc_type, generic_service_exception_handler)

    # Catch-all para qualquer outra excecao nao tratada
    app.add_exception_handler(Exception, generic_service_exception_handler)
