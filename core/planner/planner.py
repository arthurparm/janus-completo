from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from core.memory import memory_service
from core.rag import qdrant_service
from core.neo4j import neo4j_client
from core.prompt_registry import get_prompt
from core.security.lgpd import lgpd_guard
from core.agents.supervisors import get_supervisor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["planner"])

class TaskPlan(BaseModel):
    task_id: str
    description: str
    subtasks: List[Dict[str, Any]]
    dependencies: List[str]
    priority: str = "medium"
    estimated_duration_minutes: int
    requires_human_approval: bool = False
    lgpd_status: str = "compliant"

class PlannerRequest(BaseModel):
    user_input: str
    user_id: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    session_id: Optional[str] = None

class PlannerResponse(BaseModel):
    plan_id: str
    master_plan: TaskPlan
    subtasks_assigned: List[Dict]
    status: str = "created"
    message: str

async def create_hierarchical_plan(state: Dict) -> Dict:
    """Core do Top-Level Planner usando LangGraph"""
    user_input = state["user_input"]
    user_id = state["user_id"]
    
    # 1. Recupera memória relevante
    memory_context = await memory_service.get_relevant_memory(user_id, user_input)
    
    # 2. RAG com Qdrant + reranker
    rag_results = await qdrant_service.query(user_input, limit=8)
    
    # 3. Prompt do PROMPT_REGISTRY
    system_prompt = get_prompt("planner_master_v1", {
        "memory_context": memory_context,
        "rag_results": rag_results,
        "current_date": datetime.now().isoformat()
    })
    
    # 4. LLM Call (Ollama ou modelo local)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    # Aqui viria o LLM call - usando o service do projeto
    # response = await llm_service.invoke(messages)
    # parsed_plan = parse_structured_plan(response.content)
    
    # Simulação temporária - substituir pelo LLM real
    parsed_plan = {
        "description": user_input,
        "subtasks": [],
        "dependencies": [],
        "requires_human_approval": False
    }
    
    # 5. Salva grafo no Neo4j
    plan_id = f"plan_{int(datetime.now().timestamp())}"
    await neo4j_client.create_task_graph(plan_id, parsed_plan, user_id)
    
    state["plan_id"] = plan_id
    state["master_plan"] = parsed_plan
    return state

# LangGraph Workflow
workflow = StateGraph(state_schema=Dict)
workflow.add_node("planner", create_hierarchical_plan)
workflow.add_node("supervisor_dispatch", get_supervisor)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "supervisor_dispatch")
workflow.add_edge("supervisor_dispatch", END)

planner_graph = workflow.compile()

@router.post("/execute", response_model=PlannerResponse)
async def execute_plan(request: PlannerRequest, background_tasks: BackgroundTasks):
    """Endpoint principal do Hierarchical Task Planner"""
    
    # LGPD Guard - verificação obrigatória
    await lgpd_guard.check_request(request.user_id, request.user_input, "planner")
    
    initial_state = {
        "user_input": request.user_input,
        "user_id": request.user_id,
        "context": request.context,
        "session_id": request.session_id or f"sess_{datetime.now().timestamp()}"
    }
    
    try:
        result = await planner_graph.ainvoke(initial_state)
        
        response = PlannerResponse(
            plan_id=result.get("plan_id", "unknown"),
            master_plan=TaskPlan(
                task_id=result.get("plan_id", "unknown"),
                description=request.user_input,
                subtasks=result.get("master_plan", {}).get("subtasks", []),
                dependencies=[],
                requires_human_approval=result.get("master_plan", {}).get("requires_human_approval", False)
            ),
            subtasks_assigned=[],
            message="Plano hierárquico criado com sucesso"
        )
        
        # Background: dispatch para supervisors
        if result.get("master_plan"):
            background_tasks.add_task(dispatch_to_supervisors, result)
            
        return response
        
    except Exception as e:
        logger.error(f"Planner error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar plano hierárquico")

async def dispatch_to_supervisors(plan_result: Dict):
    """Dispatch das subtarefas para os supervisors"""
    # Lógica para chamar os 4 mid-level supervisors
    pass  # Implementar com get_supervisor()

# Expor o router
def get_planner_router():
    return router
