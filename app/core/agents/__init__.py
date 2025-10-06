"""
Módulo de agentes - Sistemas de agentes e gerenciamento.
"""
from .agent_manager import AgentManager
from .multi_agent_system import (
    MultiAgentSystem,
    SpecializedAgent,
    AgentRole,
    get_multi_agent_system
)
from .meta_agent import MetaAgent, get_meta_agent

__all__ = [
    "AgentManager",
    "MultiAgentSystem",
    "SpecializedAgent",
    "AgentRole",
    "get_multi_agent_system",
    "MetaAgent",
    "get_meta_agent"
]
