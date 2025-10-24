import structlog
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, validator
from starlette.requests import Request

from app.core.infrastructure import AgentType
from app.services.agent_service import AgentService, get_agent_service

router = APIRouter(tags=["Agent"])
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

@router.post("/execute", response_model=AgentResponse, summary="Envia uma instrução para um agente executar")
async def agent_execute(
        request: AgentExecutionRequest,
        http_request: Request,
        service: AgentService = Depends(get_agent_service)
):
    """
    Recebe uma solicitação, delega para o AgentService e confia nos
    exception handlers para tratar os erros de forma centralizada.
    """
    logger.info("Recebida requisição de execução de agente.",
                correlation_id=getattr(http_request.state, "correlation_id", "no-id"))

    # O código agora é limpo e focado na lógica de negócio.
    # A conversão de AgentTimeoutError -> 408 e AgentExecutionError -> 500/503
    # é feita automaticamente pelo `exception_handlers.py`.
    result = await service.execute_agent(
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
