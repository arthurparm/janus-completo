import asyncio
import sys

# Add app to path
sys.path.append("/app")

from app.core.agents.agent_manager import AgentManager, AgentType
from app.core.agents.multi_agent_system import AgentRole


async def verify_import_and_logic():
    print("--- Verifying AgentManager Refactor ---")
    try:
        manager = AgentManager()
        print("Success: AgentManager instantiated.")
    except Exception as e:
        print(f"Failed: AgentManager instantiation error: {e}")
        return

    # Check mapping
    role = manager._map_type_to_role(AgentType.ORCHESTRATOR)
    print(f"Mapping Check: ORCHESTRATOR -> {role}")
    assert role == AgentRole.PROJECT_MANAGER

    # Check arun_agent structure (mocking system to avoid real LLM calls)
    print("Verifying arun_agent logic...")

    # We can mock _system.create_agent and execute_task
    from unittest.mock import AsyncMock, MagicMock

    mock_agent = MagicMock()
    mock_agent.execute_task = AsyncMock(
        return_value={"result": "Mock Answer", "status": "completed"}
    )

    manager._system.create_agent = MagicMock(return_value=mock_agent)
    manager._system.workspace.add_task = MagicMock()

    result = await manager.arun_agent("Test Question", AgentType.ORCHESTRATOR, None)

    print(f"Result from arun_agent: {result}")
    assert result["answer"] == "Mock Answer"
    assert result["status"] == "completed"

    print("Success: arun_agent logic verified.")


if __name__ == "__main__":
    asyncio.run(verify_import_and_logic())
