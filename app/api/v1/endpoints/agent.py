# app/api/v1/endpoints/agent.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core import reasoning_core

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    generated_cypher: str | None = None

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Envia uma pergunta em linguagem natural para Janus",
    tags=["Agent"]
)
def agent_query(request: QueryRequest):
    """
    Recebe uma pergunta, usa a cadeia de RAG com o Grafo de Conhecimento
    para encontrar a resposta e a retorna.
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")
    
    result = reasoning_core.query_knowledge_graph(request.question)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # GraphCypherQAChain usually returns {"result": str, "intermediate_steps": [{"query": str, ...}], ...}
    intermediate = result.get("intermediate_steps") or []
    generated_cypher = None
    if isinstance(intermediate, list) and intermediate:
        first_step = intermediate[0] or {}
        if isinstance(first_step, dict):
            generated_cypher = first_step.get("query")

    # Prefer 'answer' (new format). Fallback to 'result' for compatibility with error paths.
    answer_text = result.get("answer")
    if answer_text is None:
        answer_text = result.get("result", "Não foi possível encontrar uma resposta.")

    return QueryResponse(
        question=request.question,
        answer=answer_text,
        generated_cypher=generated_cypher
    )
