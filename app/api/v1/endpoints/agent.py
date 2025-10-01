
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from starlette.requests import Request

from app.core.agent_manager import agent_manager, AgentType

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
        """Valida que a pergunta não é apenas espaços em branco."""
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
    com o tipo de agente especificado.

    Args:
        request: Request com pergunta e tipo de agente
        http_request: Request HTTP da FastAPI (para correlation ID)

    Returns:
        AgentResponse com resposta do agente

    Raises:
        HTTPException: Em caso de erro na execução
    """
    correlation_id = http_request.headers.get('X-Correlation-ID', 'no-id')

    logger.info(
        f"[{correlation_id}] Recebendo requisição de agente: "
        f"tipo={request.agent_type.name}, question_len={len(request.question)}"
    )

    try:
        # Executa agente de forma assíncrona (usando executor para função síncrona)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,  # usa thread pool padrão
                agent_manager.run_agent,
                request.question,
                http_request,
                request.agent_type
            ),
            timeout=_AGENT_EXECUTION_TIMEOUT
        )

        # Verifica se houve erro
        if "error" in result:
            error_msg = result["error"]
            trace_id = result.get("trace_id", correlation_id)

            logger.error(f"[{trace_id}] Erro na execução do agente: {error_msg}")

            # Determina tipo de erro
            if "timeout" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail={
                        "error": "Timeout na execução do agente",
                        "message": error_msg,
                        "trace_id": trace_id
                    }
                )
            elif "circuit" in error_msg.lower() or "circuit breaker" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "Serviço temporariamente indisponível",
                        "message": "O sistema está sobrecarregado. Tente novamente em alguns instantes.",
                        "trace_id": trace_id
                    }
                )
            elif "validação" in error_msg.lower() or "validation" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Erro de validação",
                        "message": error_msg,
                        "trace_id": trace_id
                    }
                )
            else:
                # Erro genérico
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "Erro interno na execução do agente",
                        "message": error_msg,
                        "trace_id": trace_id
                    }
                )

        logger.info(f"[{correlation_id}] Agente executado com sucesso")

        return AgentResponse(
            question=request.question,
            answer=result.get("answer", ""),
            agent_type_used=request.agent_type.name,
            intermediate_steps=result.get("intermediate_steps")
        )

    except asyncio.TimeoutError:
        logger.error(
            f"[{correlation_id}] Timeout ao executar agente após {_AGENT_EXECUTION_TIMEOUT}s"
        )
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "error": "Timeout na execução do agente",
                "message": f"A execução excedeu o tempo limite de {_AGENT_EXECUTION_TIMEOUT} segundos.",
                "trace_id": correlation_id
            }
        )

    except HTTPException:
        # Re-raise HTTPException já tratada
        raise

    except Exception as e:
        logger.error(
            f"[{correlation_id}] Erro INESPERADO ao executar agente: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Erro interno inesperado",
                "message": "Ocorreu um erro inesperado. Consulte os logs para mais detalhes.",
                "trace_id": correlation_id
            }
        )
