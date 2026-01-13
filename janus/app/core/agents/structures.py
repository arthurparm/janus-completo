from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

# --- Enums ---


class AgentRole(Enum):
    """Papéis especializados de agentes."""

    PROJECT_MANAGER = "project_manager"  # Coordenador geral
    RESEARCHER = "researcher"  # Pesquisa e análise
    CODER = "coder"  # Geração de código
    TESTER = "tester"  # Testes e validação
    DOCUMENTER = "documenter"  # Documentação
    OPTIMIZER = "optimizer"  # Otimização e refatoração
    SYSADMIN = "sysadmin"  # Administrador de Sistema (OS Agency)


class TaskStatus(Enum):
    """Status de uma tarefa."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Prioridade de uma tarefa."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# --- Modelos de Dados ---


@dataclass
class Task:
    """Representa uma tarefa no sistema multi-agente."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    assigned_to: str | None = None  # Agent ID
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)  # Task IDs
    result: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }
