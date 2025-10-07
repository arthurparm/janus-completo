import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from starlette.requests import Request

from app.core.infrastructure import AgentType
from app.core.agents import agent_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# Constantes
_MAX_QUESTION_LENGTH = 10000  # caracteres
_AGENT_EXECUTION_TIMEOUT = 120  # segundos


class AgentExecutionRequest(BaseModel):
    """Request para execução de agente."""
    question: str = Field(
        ...,
        description="Pergunta ou instrução para o agente",
        min_length=1,
        max_length=_MAX_QUESTION_LENGTH
    )
    agent_type: AgentType = Field(
        default=AgentType.TOOL_USER,
        description="Tipo de agente a ser executado"
    )

    @validator('question')
    def question_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Pergunta não pode ser vazia ou conter apenas espaços')
        return v.strip()


class AgentResponse(BaseModel):
    """Response da execução de agente."""
    question: str
    answer: str
    agent_type_used: str
    intermediate_steps: Optional[list] = None


@router.post(
    "/execute",
    response_model=AgentResponse,
    summary="Envia uma instrução para um agente Janus executar",
    tags=["Agent"],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Agente executado com sucesso"},
        400: {"description": "Erro de validação na entrada"},
        408: {"description": "Timeout na execução do agente"},
        500: {"description": "Erro interno durante execução"},
        503: {"description": "Serviço temporariamente indisponível"}
    }
)
async def agent_execute(
        request: AgentExecutionRequest,
        http_request: Request
):
    """
    Recebe uma solicitação e a encaminha para o AgentManager executar
    com o tipo de agente especificado de forma assíncrona.
    """
    correlation_id = getattr(http_request, "state", {}).correlation_id or "no-id"
    logger.info(f"[{correlation_id}] Recebendo requisição de agente: tipo={request.agent_type.name}")

    try:
        # Executa o agente de forma nativamente assíncrona
        result = await asyncio.wait_for(
            agent_manager.arun_agent(
                question=request.question,
                request=http_request,
                agent_type=request.agent_type
            ),
            timeout=_AGENT_EXECUTION_TIMEOUT
        )

        if "error" in result:
            error_msg = result["error"]
            logger.error(f"[{correlation_id}] Erro na execução do agente: {error_msg}")

            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            if "timeout" in error_msg.lower():
                status_code = status.HTTP_408_REQUEST_TIMEOUT
            elif "circuit" in error_msg.lower():
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif "validação" in error_msg.lower():
                status_code = status.HTTP_400_BAD_REQUEST

            raise HTTPException(status_code=status_code, detail={"error": error_msg, "trace_id": correlation_id})

        logger.info(f"[{correlation_id}] Agente executado com sucesso")

        return AgentResponse(
            question=request.question,
            answer=result.get("answer", ""),
            agent_type_used=request.agent_type.name,
            intermediate_steps=result.get("intermediate_steps")
        )

    except asyncio.TimeoutError:
        logger.error(f"[{correlation_id}] Timeout GERAL ao executar agente após {_AGENT_EXECUTION_TIMEOUT}s")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={"error": f"A execução excedeu o tempo limite de {_AGENT_EXECUTION_TIMEOUT} segundos."}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"[{correlation_id}] Erro INESPERADO na camada da API: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Ocorreu um erro inesperado no servidor."}
        )
