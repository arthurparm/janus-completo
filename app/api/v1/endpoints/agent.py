# app/api/v1/endpoints/agent.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

# A importação agora aponta para a nova função do agente executor
from app.core.agent_manager import agent_manager, AgentType

router = APIRouter()


class AgentExecutionRequest(BaseModel):
    question: str
    # Opcional: permite que o cliente solicite um tipo de agente específico.
    # Em um sistema real, essa decisão seria provavelmente tomada pelo Orquestrador.
    agent_type: AgentType = AgentType.TOOL_USER


class AgentResponse(BaseModel):
    question: str
    answer: str
    agent_type_used: str
    intermediate_steps: list | None = None


@router.post(
    "/execute",
    response_model=AgentResponse,
    summary="Envia uma instrução para um agente Janus executar",
    tags=["Agent"]
)

def agent_execute(request: AgentExecutionRequest, http_request: Request):
    """
    Recebe uma solicitação e a encaminha para o AgentManager executar
    com o tipo de agente especificado.
    """
    result = agent_manager.run_agent(request.question, http_request, request.agent_type)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return AgentResponse(
        question=request.question,
        answer=result.get("answer"),
        agent_type_used=request.agent_type.name,
        intermediate_steps=result.get("intermediate_steps")
    )
