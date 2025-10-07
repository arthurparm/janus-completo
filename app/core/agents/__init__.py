"""
Módulo de agentes - Sistemas de agentes e gerenciamento.
"""
from .agent_manager import AgentManager, agent_manager
from .meta_agent import MetaAgent, get_meta_agent
from .meta_agent_cycle import run_meta_agent_cycle
from .multi_agent_system import (
    MultiAgentSystem,
    SpecializedAgent,
    AgentRole,
    get_multi_agent_system
)

__all__ = [
    "AgentManager",
    "agent_manager",
    "MultiAgentSystem",
    "SpecializedAgent",
    "AgentRole",
    "get_multi_agent_system",
    "MetaAgent",
    "get_meta_agent",
    "run_meta_agent_cycle"
]
