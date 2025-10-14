import structlog
from typing import Dict, Any, List, Optional

from app.core.agents import get_multi_agent_system, AgentRole, MultiAgentSystem
from app.core.agents.multi_agent_system import Task, TaskStatus, SpecializedAgent

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

    def find_all_agents(self) -> List[Dict[str, Any]]:
        logger.debug("Buscando todos os agentes no repositório")
        return self._get_system().list_agents()

    def find_agent_by_id(self, agent_id: str) -> Optional[SpecializedAgent]:
        logger.debug("Buscando agente por ID no repositório", agent_id=agent_id)
        return self._get_system().get_agent(agent_id)

    def find_tasks_by_agent(self, agent_id: str) -> List[Task]:
        logger.debug("Buscando tarefas por agente no repositório", agent_id=agent_id)
        return self._get_system().workspace.get_tasks_by_agent(agent_id)

    def save_task(self, task: Task):
        logger.debug("Salvando tarefa no repositório", task_id=task.id)
        self._get_system().workspace.add_task(task)

    async def run_task(self, agent: SpecializedAgent, task: Task) -> Dict[str, Any]:
        logger.debug("Executando tarefa via repositório", task_id=task.id, agent_id=agent.agent_id)
        return await agent.execute_task(task)

    def find_all_tasks(self) -> List[Task]:
        return list(self._get_system().workspace.tasks.values())

    def find_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return self._get_system().workspace.get_tasks_by_status(status)

    def find_task_by_id(self, task_id: str) -> Optional[Task]:
        return self._get_system().workspace.get_task(task_id)

    async def run_project(self, description: str) -> Dict[str, Any]:
        logger.debug("Executando projeto via repositório", project_description=description)
        return await self._get_system().execute_project(description)

    def get_workspace_status(self) -> Dict[str, Any]:
        return self._get_system().get_workspace_status()

    def get_system_health(self) -> Dict[str, Any]:
        system = self._get_system()
        return {
            "status": "healthy",
            "total_agents": len(system.agents),
            "project_manager_active": system.project_manager is not None,
            "workspace_status": system.get_workspace_status()
        }


# Padrão de Injeção de Dependência: Getter para o repositório
def get_collaboration_repository() -> CollaborationRepository:
    return CollaborationRepository()
