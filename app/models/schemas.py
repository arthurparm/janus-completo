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
    CONCEPT = "Concept"
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
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    INHERITS_FROM = "INHERITS_FROM"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    IS_SYNONYM_OF = "IS_SYNONYM_OF"
    IS_A = "IS_A"
    EXAMPLE_OF = "EXAMPLE_OF"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    ENABLES = "ENABLES"
    PRODUCES = "PRODUCES"
    RESULTS_IN = "RESULTS_IN"
    RELATES_TO = "RELATES_TO"
    # Adicione outros tipos de relacionamento conforme necessário


class VectorCollection(str, Enum):
    """Nomes das coleções no Banco de Dados Vetorial (Qdrant)."""
    EPISODIC_MEMORY = "janus_episodic_memory"


class QueueName(str, Enum):
    """Nomes das filas no Message Broker (RabbitMQ)."""
    KNOWLEDGE_CONSOLIDATION = "janus.knowledge.consolidation"
    AGENT_TASKS = "janus.agent.tasks"
    NEURAL_TRAINING = "janus.neural.training"
    DATA_HARVESTING = "janus.data.harvesting"
    META_AGENT_CYCLE = "janus.meta_agent.cycle"


class TaskMessage(BaseModel):
    """
    Representa uma mensagem de tarefa para o message broker.
    """
    task_id: str
    task_type: str
    payload: dict = Field(default_factory=dict)
    timestamp: float
