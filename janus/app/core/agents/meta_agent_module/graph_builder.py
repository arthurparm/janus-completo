from typing import Literal
import logging
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.core.agents.meta_agent_module.schemas import AgentState

logger = logging.getLogger(__name__)


class MetaAgentGraphBuilder:
    """Builder for the LangGraph StateGraph."""

    def __init__(self, agent_instance):
        self.agent = agent_instance
        # Use in-memory checkpointer to keep graph execution fully async
        self.checkpointer = MemorySaver()

    def build(self):
        workflow = StateGraph(AgentState)

        # 1. Add Nodes
        workflow.add_node("monitor", self._node_monitor_wrapper)
        workflow.add_node("diagnose", self._node_diagnose_wrapper)
        workflow.add_node("plan", self._node_plan_wrapper)
        workflow.add_node("reflect", self._node_reflect_wrapper)
        workflow.add_node("execute", self._node_execute_wrapper)
        workflow.add_node("error_reflexion", self._node_error_reflexion_wrapper)
        workflow.add_node("dead_letter", self._node_dead_letter_wrapper)

        # 2. Add Edges
        workflow.add_edge(START, "monitor")

        # Monitor -> Diagnose (or End if healthy)
        workflow.add_conditional_edges(
            "monitor", self._check_health, {"healthy": END, "unhealthy": "diagnose"}
        )

        workflow.add_edge("diagnose", "plan")
        workflow.add_edge("plan", "reflect")

        # Reflexion Loop: Reflect -> Execute (Approved) OR Plan (Retry)
        workflow.add_conditional_edges(
            "reflect",
            self._check_critique,
            {"approved": "execute", "retry": "plan", "give_up": "dead_letter"},
        )

        # Execution -> Error Reflexion (if failed) or End
        workflow.add_conditional_edges(
            "execute",
            self._check_execution,
            {"completed": END, "failed": "error_reflexion"}
        )

        # Error Reflexion -> Plan (Retry) or Dead Letter
        workflow.add_conditional_edges(
            "error_reflexion",
            self._check_reflexion,
            {"retry": "plan", "give_up": "dead_letter"}
        )

        workflow.add_edge("dead_letter", END)

        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    # --- Node Wrappers (Adapter Pattern: TypedDict <-> Logic) ---

    async def _node_monitor_wrapper(self, state: AgentState) -> dict:
        # Call original method (adapted to return dict updates)
        return await self.agent.monitor_node_logic(state)

    async def _node_diagnose_wrapper(self, state: AgentState) -> dict:
        return await self.agent.diagnosis_node_logic(state)

    async def _node_plan_wrapper(self, state: AgentState) -> dict:
        return await self.agent.planning_node_logic(state)

    async def _node_reflect_wrapper(self, state: AgentState) -> dict:
        return await self.agent.reflection_node_logic(state)

    async def _node_execute_wrapper(self, state: AgentState) -> dict:
        return await self.agent.execution_node_logic(state)

    async def _node_error_reflexion_wrapper(self, state: AgentState) -> dict:
        return await self.agent.error_reflexion_node_logic(state)

    async def _node_dead_letter_wrapper(self, state: AgentState) -> dict:
        logger.critical(f"DEAD LETTER: Cycle {state.get('cycle_id')} failed after max retries.")
        # Alerting logic here
        return {"status": "dead_letter"}

    # --- Conditional Logic ---

    def _check_health(self, state: AgentState) -> Literal["healthy", "unhealthy"]:
        # If issues list is empty, it's healthy
        if not state.get("detected_issues"):
            return "healthy"
        return "unhealthy"

    def _check_execution(self, state: AgentState) -> Literal["completed", "failed"]:
        if state.get("status") == "execution_failed":
            return "failed"
        return "completed"

    def _check_reflexion(self, state: AgentState) -> Literal["retry", "give_up"]:
        if state.get("status") == "retry":
            return "retry"
        return "give_up"

    def _check_critique(self, state: AgentState) -> Literal["approved", "retry", "give_up"]:
        critique = state.get("critique", {})
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if critique.get("approved"):
            return "approved"

        if retry_count >= max_retries:
            return "give_up"

        return "retry"
