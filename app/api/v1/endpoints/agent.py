import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from starlette.requests import Request

from app.core.infrastructure import AgentType
from app.services.agent_service import agent_service, AgentTimeoutError, AgentExecutionError

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class AgentExecutionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    agent_type: AgentType = Field(default=AgentType.TOOL_USER)

    @validator('question')
    def question_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('A pergunta não pode ser vazia.')
        return v.strip()

class AgentResponse(BaseModel):
    question: str
    answer: str
    agent_type_used: str
    intermediate_steps: Optional[list] = None


# --- Endpoint ---

@router.post(
    "/execute",
    response_model=AgentResponse,
    summary="Envia uma instrução para um agente Janus executar",
    tags=["Agent"],
)
async def agent_execute(request: AgentExecutionRequest, http_request: Request):
    """
    Recebe uma solicitação, delega para o AgentService e traduz os resultados
    ou erros para uma resposta HTTP.
    """
    correlation_id = getattr(http_request.state, "correlation_id", "no-id")
    logger.info("Recebida requisição de execução de agente.", correlation_id=correlation_id)

    try:
        result = await agent_service.execute_agent(
            question=request.question,
            agent_type=request.agent_type,
            http_request=http_request
        )

        return AgentResponse(
            question=request.question,
            answer=result.get("answer", ""),
            agent_type_used=request.agent_type.name,
            intermediate_steps=result.get("intermediate_steps")
        )

    except AgentTimeoutError as e:
        logger.warning("Timeout na execução do agente", correlation_id=correlation_id)
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(e))

    except AgentExecutionError as e:
        error_msg = str(e)
        logger.error("Erro de execução no serviço de agente", error_message=error_msg, correlation_id=correlation_id)

        # Lógica para mapear o erro do serviço para um status HTTP apropriado
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "circuit" in error_msg.lower():
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        raise HTTPException(status_code=status_code, detail={"error": error_msg, "trace_id": correlation_id})

    except Exception as e:
        logger.critical("Erro inesperado na camada de API do agente", exc_info=e, correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Ocorreu um erro inesperado no servidor."}
        )
