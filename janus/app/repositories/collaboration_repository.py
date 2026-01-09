from typing import Any
from typing import Any as SpecializedAgent
from typing import Any as Task
from typing import Any as TaskStatus

import structlog

from app.core.agents import AgentRole, MultiAgentSystem, get_multi_agent_system

logger = structlog.get_logger(__name__)


class CollaborationRepositoryError(Exception):
    """Base exception for collaboration repository errors."""

    pass


class CollaborationRepository:
    """
    Camada de Repositório para o Sistema de Colaboração Multi-Agente.
    Abstrai todas as interações diretas com a infraestrutura do `MultiAgentSystem`.
    """

    def _get_system(self) -> MultiAgentSystem:
        return get_multi_agent_system()

    def create_agent(self, role: AgentRole) -> SpecializedAgent:
        logger.debug("Criando agente no repositório", role=role.value)
        return self._get_system().create_agent(role)

    def find_all_agents(self) -> list[dict[str, Any]]:
        logger.debug("Buscando todos os agentes no repositório")
        return self._get_system().list_agents()

    def find_agent_by_id(self, agent_id: str) -> SpecializedAgent | None:
        logger.debug("Buscando agente por ID no repositório", agent_id=agent_id)
        return self._get_system().get_agent(agent_id)

    def find_tasks_by_agent(self, agent_id: str) -> list[Task]:
        logger.debug("Buscando tarefas por agente no repositório", agent_id=agent_id)
        return self._get_system().workspace.get_tasks_by_agent(agent_id)

    def save_task(self, task: Task):
        logger.debug("Salvando tarefa no repositório", task_id=task.id)
        self._get_system().workspace.add_task(task)

    async def run_task(self, agent: SpecializedAgent, task: Task) -> dict[str, Any]:
        logger.debug("Executando tarefa via repositório", task_id=task.id, agent_id=agent.agent_id)
        return await agent.execute_task(task)

    def find_all_tasks(self) -> list[Task]:
        return list(self._get_system().workspace.tasks.values())

    def find_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        return self._get_system().workspace.get_tasks_by_status(status)

    def find_task_by_id(self, task_id: str) -> Task | None:
        return self._get_system().workspace.get_task(task_id)

    async def run_project(self, description: str) -> dict[str, Any]:
        logger.debug("Executando projeto via repositório", project_description=description)
        return await self._get_system().execute_project(description)

    async def run_tasks_parallel(
        self, task_ids: list[str] | None = None, concurrency: int = 4
    ) -> dict[str, Any]:
        """Executa tarefas em paralelo respeitando dependências usando o core system."""
        logger.debug(
            "Executando tarefas em paralelo via repositório",
            task_ids=task_ids,
            concurrency=concurrency,
        )
        return await self._get_system().execute_tasks_parallel(
            task_ids=task_ids, concurrency=concurrency
        )

    def get_workspace_status(self) -> dict[str, Any]:
        return self._get_system().get_workspace_status()

    def get_system_health(self) -> dict[str, Any]:
        system = self._get_system()
        return {
            "status": "healthy",
            "total_agents": len(system.agents),
            "project_manager_active": system.project_manager is not None,
            "workspace_status": system.get_workspace_status(),
        }

    # --- Shared Workspace Operations ---
    def add_artifact(self, key: str, value: Any, author: str):
        logger.debug("Adicionando artefato no workspace via repositório", key=key, author=author)
        self._get_system().workspace.add_artifact(key, value, author)

    def get_artifact(self, key: str) -> Any | None:
        logger.debug("Lendo artefato do workspace via repositório", key=key)
        return self._get_system().workspace.get_artifact(key)

    def send_message(self, from_agent: str, to_agent: str, content: str) -> dict[str, Any]:
        logger.debug("Enviando mensagem via repositório", from_agent=from_agent, to_agent=to_agent)
        system = self._get_system()
        system.workspace.send_message(from_agent, to_agent, content)
        # Retorna a última mensagem registrada (garantido pela operação acima)
        return system.workspace.messages[-1] if system.workspace.messages else {}

    def get_messages_for(self, agent_id: str) -> list[dict[str, Any]]:
        logger.debug("Recuperando mensagens para agente via repositório", agent_id=agent_id)
        return self._get_system().workspace.get_messages_for(agent_id)

    # --- System Control ---
    def shutdown_all(self):
        logger.debug("Desligando todos os agentes via repositório")
        self._get_system().shutdown_all()


# Padrão de Injeção de Dependência: Getter para o repositório
def get_collaboration_repository() -> CollaborationRepository:
    return CollaborationRepository()
