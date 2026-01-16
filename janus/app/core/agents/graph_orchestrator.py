import logging
import operator
from typing import Annotated, Literal, Sequence, TypedDict, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.core.agents.leaf_worker import LeafWorker
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.db.postgres_config import postgres_db

logger = logging.getLogger(__name__)

# Constants
GRAPH_SCHEMA_VERSION = 1

# State definition
class AgentState(TypedDict):
    schema_version: int # For versioning
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: Literal["finish", "worker", "human_approval"]
    current_worker: str | None
    worker_input: str | None
    worker_output: str | None
    approval_status: str | None # pending, approved, rejected
    error: str | None

# Nodes
async def supervisor_node(state: AgentState):
    """
    Supervisor node that routes the conversation.
    It analyzes the last message and decides whether to delegate to a worker,
    ask for human approval, or finish.
    """
    # Version check / Migration logic could be here if we wanted to migrate in-flight
    # But we rely on external cleanup for incompatible versions.
    # Just ensure we set current version if missing (new threads)
    if state.get("schema_version") is None:
        # We can't easily update state here without returning it. 
        # But this is read-only logic mostly.
        pass

    messages = state["messages"]
    last_message = messages[-1]
    
    # If we just came from a worker with output, return it
    if state.get("worker_output"):
        return {
            "messages": [AIMessage(content=f"Worker Output: {state['worker_output']}")],
            "next_step": "finish",
            "worker_output": None # Clear for next turn
        }
        
    # If we just came from approval
    if state.get("approval_status") == "approved":
        return {"next_step": "worker", "approval_status": None}
    elif state.get("approval_status") == "rejected":
        return {
            "messages": [AIMessage(content="Action rejected by user.")],
            "next_step": "finish",
            "approval_status": None
        }

    # Basic routing logic (can be replaced with LLM call)
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        
        # Example sensitive keyword detection
        if "delete" in content or "deploy" in content:
            return {
                "next_step": "human_approval", 
                "current_worker": "sysadmin",
                "worker_input": last_message.content,
                "schema_version": GRAPH_SCHEMA_VERSION
            }
            
        return {
            "next_step": "worker", 
            "current_worker": "assistant",
            "worker_input": last_message.content,
            "schema_version": GRAPH_SCHEMA_VERSION
        }
        
    return {"next_step": "finish", "schema_version": GRAPH_SCHEMA_VERSION}

async def worker_node(state: AgentState):
    """
    Executes the selected leaf worker.
    """
    worker_name = state.get("current_worker", "assistant")
    prompt = state.get("worker_input", "")
    
    # Instantiate PydanticAI worker
    # In a real scenario, we would have a factory or registry of workers
    prompt_name = "leaf_worker_assistant"
    if worker_name == "sysadmin":
        prompt_name = "leaf_worker_sysadmin"

    system_prompt = await get_formatted_prompt(prompt_name)

    worker = LeafWorker(name=worker_name, system_prompt=system_prompt)
    
    try:
        result = await worker.run(prompt)
        return {"worker_output": result.response, "next_step": "supervisor"}
    except Exception as e:
        logger.error(f"Worker execution failed: {e}")
        return {"error": str(e), "next_step": "finish"}

async def human_approval_node(state: AgentState):
    """
    Node that represents the state of waiting for human approval.
    This node doesn't do much because the graph interrupts BEFORE it.
    When resumed, it passes control back to supervisor.
    """
    # If we are here, it means we were resumed.
    # The external API should update 'approval_status' in the state before resuming.
    return {"next_step": "supervisor"}

# Graph Construction
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance:
        return _graph_instance

    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("worker", worker_node)
    workflow.add_node("human_approval", human_approval_node)
    
    workflow.add_edge(START, "supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_step"],
        {
            "worker": "worker",
            "human_approval": "human_approval",
            "finish": END
        }
    )
    
    workflow.add_edge("worker", "supervisor")
    workflow.add_edge("human_approval", "supervisor")
    
    # Setup Checkpointer using shared async pool
    try:
        # Initialize checkpointer with shared connection pool
        # AsyncPostgresSaver accepts an async connection pool
        checkpointer = AsyncPostgresSaver(postgres_db.engine)
        
        # We need to run setup() on the checkpointer to create tables if they don't exist
        # But setup() is an async method in AsyncPostgresSaver.
        # Since get_graph is synchronous (called at module level or on demand), 
        # we can't await here easily without creating a new loop or assuming it's called in async context.
        # Ideally, checkpointer setup should happen at app startup.
        # For now, we assume tables are created or will be created by init_database()
        
        _graph_instance = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_approval"]
        )
        
        # Configure recursion limit from settings
        # Note: compile() returns a CompiledGraph which doesn't expose recursion_limit property directly
        # The recursion limit is actually passed during invoke(), not compile().
        # However, we can set a default config here if we wrap invoke, but standard usage is passing config at runtime.
        # We will document that callers should respect settings.REASONING_MAX_ITERATIONS.
        
    except Exception as e:
        logger.warning(f"Failed to initialize AsyncPostgresSaver: {e}. Falling back to MemorySaver.")
        from langgraph.checkpoint.memory import MemorySaver
        _graph_instance = workflow.compile(checkpointer=MemorySaver(), interrupt_before=["human_approval"])
        
    return _graph_instance
