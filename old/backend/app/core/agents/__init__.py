from importlib import import_module
from typing import Any

_LAZY_EXPORTS = {
    "AgentManager": ".agent_manager",
    "get_agent_manager": ".agent_manager",
    "MetaAgent": ".meta_agent",
    "get_meta_agent": ".meta_agent",
    "AgentRole": ".multi_agent_system",
    "MultiAgentSystem": ".multi_agent_system",
    "get_multi_agent_system": ".multi_agent_system",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "AgentManager",
    "AgentRole",
    "MetaAgent",
    "MultiAgentSystem",
    "get_agent_manager",
    "get_meta_agent",
    "get_multi_agent_system",
]
