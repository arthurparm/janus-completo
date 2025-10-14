import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# --- Schemas de Dados ---

class Experience(BaseModel):
    """
    Representa uma única experiência ou evento a ser memorizado.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: str
    content: str
    metadata: dict = Field(default_factory=dict)


# --- Constantes e Enums da Aplicação ---

class GraphLabel(str, Enum):
    """Labels para nós no Grafo de Conhecimento (Neo4j)."""
    FILE = "File"
    CODE_FILE = "CodeFile"
    FUNCTION = "Function"
    CODE_FUNCTION = "CodeFunction"
    CLASS = "Class"
    CODE_CLASS = "CodeClass"
    ENTITY = "Entity"
    SKILL = "Skill"
    TASK = "Task"
    WORKFLOW = "Workflow"
    STEP = "Step"
    REFLECTION = "Reflection"
    RELATIONSHIP_TYPE = "RelationshipType"


class GraphRelationship(str, Enum):
    """Tipos de relacionamento no Grafo de Conhecimento (Neo4j)."""
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IS_SYNONYM_OF = "IS_SYNONYM_OF"
    # Adicione outros tipos de relacionamento conforme necessário


class VectorCollection(str, Enum):
    """Nomes das coleções no Banco de Dados Vetorial (Qdrant)."""
    EPISODIC_MEMORY = "janus_episodic_memory"


class QueueName(str, Enum):
    """Nomes das filas no Message Broker (RabbitMQ)."""
    KNOWLEDGE_CONSOLIDATION = "janus.knowledge.consolidation"
