import pytest

from app.core.agents.meta_agent import MetaAgent
from app.core.agents.structures import AgentRole
from app.core.agents.workspace import SharedWorkspace


class DummyAgent:
    def __init__(self, role: AgentRole):
        self.role = role

    async def execute_task(self, task):
        task.status = "completed"
        return {
            "task_id": task.id,
            "status": "completed",
            "result": f"done by {self.role.value}",
            "attempts": 1,
            "duration_seconds": 0.1,
        }


class DummySystem:
    def __init__(self):
        self.workspace = SharedWorkspace()
        self.created_roles = []

    async def create_agent(self, role: AgentRole):
        self.created_roles.append(role)
        return DummyAgent(role)


@pytest.mark.asyncio
async def test_dispatch_task_executes_agent():
    agent = MetaAgent()
    dummy_system = DummySystem()
    agent.executor = dummy_system

    recommendation = {
        "title": "Check MemoryCore Initialization",
        "description": "Verify collection_name exists",
        "priority": 1,
        "suggested_agent": "coder",
        "category": "reliability",
    }
    state = {"cycle_id": "cycle_test", "diagnosis": "Test diagnosis", "detected_issues": []}

    result = await agent._dispatch_task(recommendation, state)

    assert result["status"] == "completed"
    assert result["agent_role"] == AgentRole.CODER.value
    assert dummy_system.created_roles == [AgentRole.CODER]
    assert len(dummy_system.workspace.tasks) == 1


@pytest.mark.asyncio
async def test_execution_node_marks_partial_when_failed(monkeypatch):
    agent = MetaAgent()

    async def _fake_dispatch(rec, state):
        if rec["title"] == "Fail":
            return {"title": "Fail", "status": "failed", "agent_role": "tester"}
        return {"title": rec["title"], "status": "completed", "agent_role": "coder"}

    monkeypatch.setattr(agent, "_dispatch_task", _fake_dispatch)

    state = {
        "final_plan": [{"title": "Ok"}, {"title": "Fail"}],
        "status": "approved",
    }

    result = await agent.execution_node_logic(state)

    assert result["status"] == "partial"
    assert len(result["execution_results"]) == 2
