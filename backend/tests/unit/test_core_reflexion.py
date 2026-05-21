import sys
from unittest.mock import AsyncMock, MagicMock, patch

# --- Pre-import Mocks to bypass DB initialization ---
mock_pg_config = MagicMock()
mock_pg_config.postgres_db = MagicMock()
sys.modules["app.db.postgres_config"] = mock_pg_config
# ----------------------------------------------------

import pytest
from app.core.agents.meta_agent_module.graph_builder import MetaAgentGraphBuilder
from app.core.agents.meta_agent import MetaAgent
from app.core.agents.meta_agent_module.schemas import AgentState, ReflexionAnalysisSchema

class MockAgent:
    async def monitor_node_logic(self, state): 
        # Return unhealthy to force flow into diagnose -> plan
        return {"detected_issues": [{"id": "test_issue"}]}
    async def diagnosis_node_logic(self, state): return {"diagnosis": "test_diag"}
    async def planning_node_logic(self, state): return {"final_plan": [{"title": "test_task"}]}
    async def reflection_node_logic(self, state): return {"critique": {"approved": True}}
    async def execution_node_logic(self, state): 
        # Fail first time, succeed second time? Or just fail always to test loop
        if state.get("retry_count", 0) == 0:
            return {"status": "execution_failed", "execution_error": "Simulated Error"}
        return {"status": "completed"}
        
    async def error_reflexion_node_logic(self, state):
        return {"status": "retry", "retry_count": state.get("retry_count", 0) + 1}

@pytest.mark.asyncio
async def test_reflexion_graph_flow():
    """Test that the graph routes to error_reflexion on failure."""
    agent = MockAgent()
    builder = MetaAgentGraphBuilder(agent)
    builder.checkpointer = None # Disable persistence for simple unit test
    app = builder.build()
    
    initial_state = {
        "cycle_id": "test_cycle",
        "retry_count": 0,
        "max_retries": 3,
        "detected_issues": [{"id": "force_unhealthy"}]
    }
    
    # monitor(unhealthy) -> diagnose -> plan -> reflect(approved) -> execute(fail) -> error_reflexion -> plan -> reflect -> execute(success) -> END
    
    result = await app.ainvoke(initial_state)
    
    assert result["retry_count"] == 1
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_error_reflexion_logic():
    """Test the actual MetaAgent logic for error reflexion."""
    
    # Mock LLM and WorkingMemory
    with patch("app.core.agents.meta_agent.get_llm") as mock_get_llm, \
         patch("app.core.agents.meta_agent.get_working_memory") as mock_get_wm:
        
        # get_llm is async, so it returns a Future that resolves to the LLM object
        # The LLM object itself should have sync methods like with_structured_output
        mock_llm = MagicMock() 
        mock_get_llm.return_value = mock_llm
        
        mock_structured_llm = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        
        mock_wm = MagicMock()
        mock_get_wm.return_value = mock_wm
        
        # Setup LLM response
        analysis_result = ReflexionAnalysisSchema(
            root_cause="Logic error in sorting",
            error_type="LogicError",
            actionable_insights=["Use stable sort", "Check keys"]
        )
        mock_structured_llm.ainvoke.return_value = analysis_result
        
        agent = MetaAgent()
        # Avoid full init
        agent.llm = mock_llm 
        
        state: AgentState = {
            "cycle_id": "test_cycle",
            "execution_error": "IndexError: list index out of range",
            "final_plan": [{"title": "Sort List"}],
            "diagnosis": "Initial diagnosis",
            "retry_count": 0,
            "max_retries": 3
        }
        
        # Run logic
        new_state = await agent.error_reflexion_node_logic(state)
        
        # Verify LLM called
        mock_llm.with_structured_output.assert_called_once()
        mock_structured_llm.ainvoke.assert_called_once()
        
        # Verify Memory Update
        mock_wm.add.assert_called_once()
        args, kwargs = mock_wm.add.call_args
        assert kwargs["type"] == "reflexion"
        assert "Logic error" in kwargs["content"]
        
        # Verify State Update
        assert new_state["status"] == "retry"
        assert new_state["retry_count"] == 1
        assert new_state["error_analysis"]["root_cause"] == "Logic error in sorting"
