import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.agents.structures import Task, TaskStatus
from app.core.agents.metrics import AGENT_COLLABORATION_COUNTER

logger = logging.getLogger(__name__)


@dataclass
class SharedWorkspace:
    """Espaço de trabalho compartilhado entre agentes."""

    artifacts: dict[str, Any] = field(default_factory=dict)  # Arquivos, dados, resultados
    messages: list[dict[str, Any]] = field(default_factory=list)  # Mensagens entre agentes
    tasks: dict[str, Task] = field(default_factory=dict)  # Tarefas do projeto

    def add_artifact(self, key: str, value: Any, author: str):
        """Adiciona um artefato ao workspace."""
        self.artifacts[key] = {
            "value": value,
            "author": author,
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"Artefato '{key}' adicionado ao workspace por {author}")

    def get_artifact(self, key: str) -> Any | None:
        """Recupera um artefato do workspace."""
        artifact = self.artifacts.get(key)
        return artifact["value"] if artifact else None

    def send_message(self, from_agent: str, to_agent: str, content: str):
        """Envia uma mensagem entre agentes."""
        message = {
            "id": str(uuid.uuid4()),
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        self.messages.append(message)
        AGENT_COLLABORATION_COUNTER.labels(initiator=from_agent, collaborator=to_agent).inc()
        logger.info(f"Mensagem enviada: {from_agent} → {to_agent}")

    def get_messages_for(self, agent_id: str) -> list[dict[str, Any]]:
        """Recupera mensagens destinadas a um agente."""
        return [msg for msg in self.messages if msg["to"] == agent_id]

    def add_task(self, task: Task):
        """Adiciona uma tarefa ao workspace."""
        self.tasks[task.id] = task
        logger.info(f"Tarefa '{task.id}' adicionada: {task.description}")

    def get_task(self, task_id: str) -> Task | None:
        """Recupera uma tarefa pelo ID."""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Recupera tarefas por status."""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_agent(self, agent_id: str) -> list[Task]:
        """Recupera tarefas atribuídas a um agente."""
        return [task for task in self.tasks.values() if task.assigned_to == agent_id]

    def get_ready_tasks(self) -> list[Task]:
        """Retorna tarefas PENDING cujas dependências já estão COMPLETED.

        Tarefas com dependências inexistentes ou falhas não são consideradas prontas.
        """
        ready: list[Task] = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps = task.dependencies or []
            if not deps:
                ready.append(task)
                continue
            all_ok = True
            for dep_id in deps:
                dep = self.tasks.get(dep_id)
                if dep is None:
                    all_ok = False
                    break
                if dep.status != TaskStatus.COMPLETED:
                    all_ok = False
                    break
            if all_ok:
                ready.append(task)
        return ready
