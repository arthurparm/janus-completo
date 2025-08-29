# app/core/schemas.py
from enum import Enum

class AgentType(Enum):
    """
    Define os papéis especializados dos agentes dentro do ecossistema Janus.
    """
    ORCHESTRATOR = "orchestrator"
    TOOL_USER = "tool_user"
    META_AGENT = "meta_agent"

class ModelRole(Enum):
    """Define os papéis cognitivos para seleção do modelo apropriado."""
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"

class ModelPriority(Enum):
    """Define a prioridade para o roteador de modelos, balanceando custo e performance."""
    LOCAL_ONLY = "local_only"
    FAST_AND_CHEAP = "fast_and_cheap"
    HIGH_QUALITY = "high_quality"