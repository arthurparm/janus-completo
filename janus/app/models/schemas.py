import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import msgpack
from pydantic import BaseModel, Field

# --- Schemas de Dados ---


class ExperienceMetadata(BaseModel):
    source_task_id: str | None = None
    original_goal: str | None = None
    origin: str | None = None
    source_agent: str | None = None
    status: str | None = None
    ts_ms: int | None = None

    class Config:
        extra = "allow"

    def get(self, key: str, default: Any | None = None) -> Any | None:
        return getattr(self, key, default)


class Experience(BaseModel):
    """
    Representa uma única experiência ou evento a ser memorizado.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    type: str
    content: str
    metadata: ExperienceMetadata = Field(default_factory=ExperienceMetadata)


class ScoredExperience(Experience):
    """
    Experience enriquecida com score de similaridade/busca.
    """

    score: float | None = None


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
    DOCUMENT = "Document"
    # JARVIS / Agentic Nodes
    USER = "User"
    USER_PREFERENCE = "UserPreference"
    GOAL = "Goal"
    PLAN = "Plan"
    ACTION = "Action"
    EPISODE = "Episode"
    MENTAL_STATE = "MentalState"
    ISSUE = "Issue"
    OUTCOME = "Outcome"


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
    MENTIONS = "MENTIONS"
    CAUSES = "CAUSES"
    SOLVES = "SOLVES"
    CAUSED_BY = "CAUSED_BY"
    SOLVED_BY = "SOLVED_BY"
    HAS_PROPERTY = "HAS_PROPERTY"
    SIMILAR_TO = "SIMILAR_TO"
    FOLLOWED_BY = "FOLLOWED_BY"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    # JARVIS / Agentic Relations
    HAS_GOAL = "HAS_GOAL"
    HAS_PREFERENCE = "HAS_PREFERENCE"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    EXECUTES = "EXECUTES"
    NEXT = "NEXT"  # Temporal sequence
    TRUSTS = "TRUSTS"
    BLOCKED_BY = "BLOCKED_BY"
    COMPLETED_BY = "COMPLETED_BY"
    CREATED_BY = "CREATED_BY"
    MODIFIED_BY = "MODIFIED_BY"
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
    REFLEXION_TASKS = "janus.tasks.reflexion"
    FAILURE_DETECTED = "janus.failure.detected"
    # Parlamento: novas filas de roteamento e agentes inteligentes
    TASKS_ROUTER = "janus.tasks.router"
    TASKS_AGENT_CODER = "janus.tasks.agent.coder"
    TASKS_AGENT_PROFESSOR = "janus.tasks.agent.professor"
    TASKS_AGENT_SANDBOX = "janus.tasks.agent.sandbox"
    TASKS_AGENT_THINKER = "janus.tasks.agent.thinker"
    TASKS_AGENT_RED_TEAM = "janus.tasks.agent.red_team"
    TASKS_KNOWLEDGE_DISTILLATION = "janus.knowledge.distillation"
    PRODUCTIVITY_GOOGLE = "janus.productivity.google"


class TaskMessage(BaseModel):
    """
    Representa uma mensagem de tarefa para o message broker.
    """

    task_id: str
    task_type: str
    payload: dict = Field(default_factory=dict)
    timestamp: float

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    def from_msgpack(data: bytes) -> "TaskMessage":
        obj = msgpack.unpackb(data, raw=False)
        return TaskMessage(**obj)


class TaskStateEvent(BaseModel):
    """Evento de histórico de um TaskState."""

    agent_role: str | None = None
    action: str
    notes: str | None = None
    reasoning: str | None = None  # Chain of Thought / Reasoning Trace
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())


class SystemStatusResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime


class ServiceStatusResponse(BaseModel):
    name: str
    status: str
    message: str
    last_check: datetime


class WorkerStatusResponse(BaseModel):
    id: str
    status: str
    last_heartbeat: datetime
    tasks_processed: int


class SystemOverviewResponse(BaseModel):
    system_status: SystemStatusResponse
    services_status: list[ServiceStatusResponse]
    workers_status: list[WorkerStatusResponse]


class AgentPayload(BaseModel):
    """Payload estruturado para TaskState."""

    context: str | None = None
    thinker_plan: str | None = None
    script_code: str | None = None
    self_healing_iterations: int | None = None
    tool_output: str | None = None
    sandbox_output: str | None = None
    sandbox_error: str | None = None
    review_notes: str | None = None
    approved: bool | None = None
    execution_result: str | None = None
    security_audit: str | None = None
    audit_passed: bool | None = None
    security_feedback: str | None = None
    code: str | None = None  # Legacy/Generic
    response: str | None = None  # Legacy/Generic

    class Config:
        extra = "allow"


class TaskState(BaseModel):
    """
    Objeto de colaboração rico compartilhado entre agentes.

    - Os agentes atualizam `data_payload` e `history` a cada passo.
    - `next_agent_role` define para qual agente o estado deve ser roteado.
    """

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_goal: str
    current_agent_role: str | None = None
    next_agent_role: str | None = None
    data_payload: AgentPayload = Field(default_factory=AgentPayload)
    history: list[TaskStateEvent] = Field(default_factory=list)
    status: str = Field(default="in_progress")
    retries: int = Field(default=0)
    meta: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    # Stateful Workers: Context Caching
    context_cached: bool = Field(default=False)
    static_context_hash: str | None = Field(default=None)

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @staticmethod
    def from_msgpack(data: bytes) -> "TaskState":
        obj = msgpack.unpackb(data, raw=False)
        return TaskState(**obj)
