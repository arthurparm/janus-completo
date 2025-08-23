# app/api/v1/endpoints/agent.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# A importação agora aponta para a nova função do agente executor
from app.core.reasoning_core import run_agent_executor

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class AgentResponse(BaseModel):
    question: str
    answer: str
    intermediate_steps: list | None = None

@router.post(
    "/execute", # Renomeamos para refletir que é uma execução, não apenas uma consulta
    response_model=AgentResponse,
    summary="Envia uma instrução para o agente Janus executar",
    tags=["Agent"]
)
def agent_execute(request: QueryRequest):
    result = run_agent_executor(request.question)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return AgentResponse(
        question=request.question,
        answer=result.get("answer"),
        intermediate_steps=result.get("intermediate_steps")
    )
