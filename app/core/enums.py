from enum import Enum


class AgentType(Enum):
    """Define os papéis especializados dos agentes dentro do ecossistema Janus."""
    ORCHESTRATOR = "orchestrator"
    TOOL_USER = "tool_user"
    META_AGENT = "meta_agent"
    REFLEXION_AGENT = "reflexion_agent"  # Sprint 5: Agente de autorreflexão e aprendizado com erros
