import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

# Importa as exceções customizadas de cada serviço
from app.services.agent_service import AgentServiceError, AgentTimeoutError
from app.services.collaboration_service import CollaborationServiceError, AgentNotFoundError, TaskNotFoundError
from app.services.context_service import ContextServiceError
from app.services.knowledge_service import KnowledgeServiceError
from app.services.learning_service import LearningServiceError, ModelNotFoundError, TrainingFailedError
from app.services.llm_service import LLMServiceError, LLMTimeoutError, LLMInvocationError
from app.services.memory_service import MemoryServiceError
from app.services.meta_agent_service import MetaAgentServiceError
from app.services.observability_service import ObservabilityServiceError, MessageNotFoundError
from app.services.optimization_service import OptimizationServiceError
from app.services.sandbox_service import SandboxError, InvalidInputError
from app.services.task_service import TaskServiceError
from app.services.tool_service import ToolServiceError, ToolNotFoundError, ProtectedToolError, ToolCreationError

logger = structlog.get_logger(__name__)

# --- Mapeamento de Exceções para Status HTTP ---

# Exceções que indicam que um recurso não foi encontrado (404)
NOT_FOUND_EXCEPTIONS = (
    AgentNotFoundError,
    TaskNotFoundError,
    ModelNotFoundError,
    MessageNotFoundError,
    ToolNotFoundError,
)

# Exceções que indicam uma entrada inválida do cliente (400)
BAD_REQUEST_EXCEPTIONS = (
    InvalidInputError,
    ProtectedToolError,
    ToolCreationError,
    TrainingFailedError,
    ValueError,  # Captura erros de validação de enum, etc.
)

# Exceções que indicam um timeout (408)
TIMEOUT_EXCEPTIONS = (
    AgentTimeoutError,
    LLMTimeoutError,
)


# --- Handlers Genéricos ---

async def http_404_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Recurso não encontrado", exc_info=exc, url=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


async def http_400_bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Requisição inválida", exc_info=exc, url=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def http_408_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Timeout na operação do serviço", exc_info=exc, url=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={"detail": str(exc)},
    )


async def generic_service_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Erro inesperado no serviço", exc_info=exc, url=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Ocorreu um erro interno no serviço: {exc}"},
    )


# --- Função para registrar todos os handlers ---

def add_exception_handlers(app):
    """Adiciona todos os manipuladores de exceção customizados à aplicação FastAPI."""
    logger.info("Registrando manipuladores de exceção customizados.")

    exception_map = {
        **{exc: http_404_not_found_handler for exc in NOT_FOUND_EXCEPTIONS},
        **{exc: http_400_bad_request_handler for exc in BAD_REQUEST_EXCEPTIONS},
        **{exc: http_408_timeout_handler for exc in TIMEOUT_EXCEPTIONS},
    }

    for exc_type, handler in exception_map.items():
        app.add_exception_handler(exc_type, handler)

    # Handler genérico para todas as outras exceções de serviço
    all_service_exceptions = (
        AgentServiceError, CollaborationServiceError, ContextServiceError,
        KnowledgeServiceError, LearningServiceError, LLMServiceError,
        MemoryServiceError, MetaAgentServiceError, ObservabilityServiceError,
        OptimizationServiceError, SandboxError, TaskServiceError, ToolServiceError
    )
    for exc_type in all_service_exceptions:
        if exc_type not in exception_map:
            app.add_exception_handler(exc_type, generic_service_exception_handler)
