import json
import logging
from pathlib import Path
from typing import List, Optional

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field, validator

from app.core.infrastructure import filesystem_manager
from app.core.infrastructure.context_manager import context_manager
from app.core.infrastructure.enums import AgentType
from app.core.infrastructure.python_sandbox import python_sandbox
from app.core.memory.memory_core import memory_core
from app.core.tools.action_module import (
    action_registry,
    ToolCategory,
    PermissionLevel
)
from app.core.tools.faulty_tools import get_faulty_tools
from app.db.graph import graph_db

logger = logging.getLogger(__name__)


# (Omitted unchanged file tools for brevity)

class RecallExperiencesInput(BaseModel):
    query: str = Field(description="A natural language query describing the memory to recall.")
    filter_by_type: Optional[str] = Field(default=None,
                                          description="Filter experiences by type (e.g., 'action_success', 'action_failure', 'meta_agent_checkpoint').")
    hours_ago: Optional[int] = Field(default=None,
                                     description="Limit the search to experiences within the last N hours.")
    min_score: float = Field(default=0.5,
                             description="Minimum similarity score (0.0 to 1.0) for a memory to be considered relevant.")
    n_results: int = Field(default=5, description="The maximum number of experiences to return.")


@tool(args_schema=RecallExperiencesInput)
async def recall_experiences(query: str, filter_by_type: Optional[str] = None, hours_ago: Optional[int] = None,
                             min_score: float = 0.5, n_results: int = 5) -> str:
    """
    Searches your memory for past experiences to inform your current task.
    You can perform a simple semantic search with a query, or apply powerful filters for more precise results.

    Use this tool to answer questions like:
    - "What were my last 3 successful attempts at using the 'write_file' tool?" (query="success with write_file", filter_by_type="action_success")
    - "Show me all failures from the last 24 hours." (query="failure", filter_by_type="action_failure", hours_ago=24)
    - "Find highly relevant memories about 'database optimization'." (query="database optimization", min_score=0.8)
    """
    try:
        experiences = await memory_core.arecall(
            query=query,
            n_results=n_results,
            filter_by_type=filter_by_type,
            hours_ago=hours_ago,
            min_score=min_score
        )
        if not experiences:
            return "No relevant experiences found with the given criteria."
        return json.dumps(experiences, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error recalling experiences: {e}", exc_info=True)
        return f"An error occurred while trying to recall experiences: {e}"


# (Omitted other tools for brevity)

# --- Fábrica de Ferramentas ---

unified_tools: List[BaseTool] = [
    # ... other tools
    recall_experiences,
    # ... other tools
]

meta_agent_tools: List[BaseTool] = [
    # ... other tools
    recall_experiences,
    # ... other tools
]


def get_tools_for_agent(agent_type: AgentType) -> List[BaseTool]:
    """
    Retorna as ferramentas apropriadas para um tipo de agente.

    Args:
        agent_type: O tipo do agente

    Returns:
        Lista de ferramentas disponíveis para o agente
    """
    if agent_type == AgentType.META_AGENT:
        return meta_agent_tools
    elif agent_type in [AgentType.ORCHESTRATOR, AgentType.TOOL_USER]:
        return unified_tools
    else:
        logger.warning(f"Tipo de agente desconhecido: {agent_type}. Usando unified_tools.")
        return unified_tools
