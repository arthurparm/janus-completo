from .agent_manager import AgentManager, get_agent_manager
try:
    from .multi_agent_system import MultiAgentSystem, get_multi_agent_system, AgentRole
except Exception:
    class AgentRole:  # type: ignore
        def __init__(self, value: str = "generic"):
            self.value = value

    class _StubMAS:  # type: ignore
        def create_agent(self, role: AgentRole):
            return type("StubAgent", (), {"agent_id": "stub", "role": role})()
        def update_agent_config(self, agent_id: str, config):
            return True
        def list_agents(self):
            return [{"agent_id": "stub", "role": "generic"}]
        def get_workspace_status(self):
            return {"workspace": "ok"}

    def get_multi_agent_system():  # type: ignore
        return _StubMAS()
    MultiAgentSystem = _StubMAS  # type: ignore

try:
    from .meta_agent import MetaAgent, get_meta_agent
except Exception:
    class MetaAgent:  # type: ignore
        async def run_cycle(self):
            return {"status": "skipped"}
    def get_meta_agent():  # type: ignore
        return MetaAgent()

__all__ = [
    "AgentManager",
    "get_agent_manager",
    "MultiAgentSystem",
    "get_multi_agent_system",
    "MetaAgent",
    "get_meta_agent",
    "AgentRole",
]
