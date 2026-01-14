import logging
import json
import re
from typing import Annotated, Literal, TypedDict
import operator

from langgraph.graph import END, START, StateGraph

from app.core.llm import ModelPriority, ModelRole
from app.repositories.llm_repository import LLMRepository
from app.services.llm_service import LLMService
from app.core.prompts.modules.debate import PROPONENT_SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class DebateState(TypedDict):
    task_id: str
    goal: str
    code: str | None
    critique: dict | None
    iteration: int
    max_iterations: int
    status: str # "in_progress", "approved", "max_iterations"
    history: Annotated[list[str], operator.add]

async def propose_node(state: DebateState):
    logger.info(f"Debate Propose Node: Iteration {state['iteration']}")
    llm = LLMService(LLMRepository())
    
    goal = state['goal']
    code = state.get('code')
    critique = state.get('critique')
    
    prompt = [
        f"OBJETIVO: {goal}",
        f"INSTRUÇÕES DO SISTEMA:\n{PROPONENT_SYSTEM_PROMPT}"
    ]
    
    if code:
        prompt.append(f"CÓDIGO ANTERIOR:\n```python\n{code}\n```")
    if critique:
        prompt.append(f"CRÍTICA (Corrigir):\n{json.dumps(critique, indent=2)}")
        
    prompt.append("Gere a solução completa (ou corrigida) agora.")
    final_prompt = "\n\n".join(prompt)
        
    result = llm.invoke_llm(prompt=final_prompt, role=ModelRole.CODE_GENERATOR, priority=ModelPriority.HIGH_QUALITY)
    response = result.get("response", "")
    
    # Extract code
    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    if not match:
         match = re.search(r"```\n(.*?)```", response, re.DOTALL)
    new_code = match.group(1) if match else response
    
    return {"code": new_code, "iteration": state["iteration"] + 1, "history": [f"Proponent generated code (Iter {state['iteration']})"]}

async def critique_node(state: DebateState):
    logger.info("Debate Critique Node")
    llm = LLMService(LLMRepository())
    
    goal = state['goal']
    code = state['code']
    
    prompt = f"OBJETIVO: {goal}\n\nCÓDIGO:\n```python\n{code}\n```\n\nINSTRUÇÕES:\n{CRITIC_SYSTEM_PROMPT}"
    
    result = llm.invoke_llm(prompt=prompt, role=ModelRole.PRIMARY_ASSISTANT, priority=ModelPriority.HIGH_QUALITY)
    response = result.get("response", "")
    
    try:
        match = re.search(r"```json\n(.*?)```", response, re.DOTALL)
        if not match: match = re.search(r"\{.*\}", response, re.DOTALL)
        
        json_str = match.group(1) if match and "json" in match.group(0) else (match.group(0) if match else response)
        json_str = json_str.replace("```json", "").replace("```", "").strip()
        critique = json.loads(json_str)
    except Exception as e:
        logger.error(f"Error parsing critique JSON: {e}")
        critique = {
            "approved": False, 
            "issues": [{"description": "Parse Error", "severity": "critical"}], 
            "general_comments": f"Failed to parse critic output: {response[:100]}..."
        }
        
    return {"critique": critique, "history": [f"Critic analyzed: Approved={critique.get('approved')}"]}

def decide_node(state: DebateState):
    critique = state.get("critique", {})
    if critique.get("approved"):
        return "finish"
    
    if state["iteration"] >= state["max_iterations"]:
        return "finish"
        
    return "propose"

# Graph Construction
workflow = StateGraph(DebateState)
workflow.add_node("propose", propose_node)
workflow.add_node("critique", critique_node)

workflow.add_edge(START, "propose")
workflow.add_edge("propose", "critique")

workflow.add_conditional_edges(
    "critique",
    decide_node,
    {
        "propose": "propose",
        "finish": END
    }
)

debate_graph = workflow.compile()
