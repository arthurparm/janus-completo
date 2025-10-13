import structlog
from typing import Dict, Any, List, Optional

from app.repositories.collaboration_repository import collaboration_repository, CollaborationRepositoryError
from app.core.agents import AgentRole
from app.core.agents.multi_agent_system import Task, TaskPriority, TaskStatus

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class CollaborationServiceError(Exception):
    """Base exception for collaboration service errors."""
    pass


class AgentNotFoundError(CollaborationServiceError):
    """Raised when an agent is not found."""
    pass


class TaskNotFoundError(CollaborationServiceError):
    """Raised when a task is not found."""
    pass


# --- Collaboration Service ---

class CollaborationService:
    """
    Camada de serviço para o sistema de colaboração multi-agente.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def create_agent(self, role: AgentRole) -> Dict[str, Any]:
        logger.info("Orquestrando criação de agente via serviço", role=role.value)
        agent = collaboration_repository.create_agent(role)
        return {"agent_id": agent.agent_id, "role": agent.role.value}

    def list_agents(self) -> List[Dict[str, Any]]:
        logger.info("Orquestrando listagem de agentes via serviço")
        return collaboration_repository.find_all_agents()

    def get_agent_details(self, agent_id: str) -> Dict[str, Any]:
        logger.info("Orquestrando busca de detalhes do agente", agent_id=agent_id)
        agent = collaboration_repository.find_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")

        tasks = collaboration_repository.find_tasks_by_agent(agent_id)
        return {
            "agent_id": agent.agent_id,
            "role": agent.role.value,
            "total_tasks": len(tasks),
            "tasks_by_status": {
                status.value: len([t for t in tasks if t.status == status])
                for status in TaskStatus
            }
        }

    def create_task(self, description: str, priority: TaskPriority, assigned_to: Optional[str],
                    dependencies: List[str]) -> Task:
        logger.info("Orquestrando criação de tarefa via serviço", description=description)
        task = Task(description=description, priority=priority, assigned_to=assigned_to, dependencies=dependencies)
        collaboration_repository.save_task(task)
        return task

    async def execute_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        logger.info("Orquestrando execução de tarefa via serviço", task_id=task_id, agent_id=agent_id)
        agent = collaboration_repository.find_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")
        task = collaboration_repository.find_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Tarefa '{task_id}' não encontrada.")
        return await collaboration_repository.run_task(agent, task)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        logger.info("Orquestrando listagem de tarefas via serviço", status=status)
        if status:
            return collaboration_repository.find_tasks_by_status(status)
        return collaboration_repository.find_all_tasks()

    def get_task_details(self, task_id: str) -> Task:
        logger.info("Orquestrando busca de detalhes da tarefa", task_id=task_id)
        task = collaboration_repository.find_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Tarefa '{task_id}' não encontrada.")
        return task

    async def execute_project(self, description: str) -> Dict[str, Any]:
        logger.info("Orquestrando execução de projeto via serviço", project_description=description)
        try:
            return await collaboration_repository.run_project(description)
        except Exception as e:
            logger.error("Erro no repositório ao executar projeto", exc_info=e)
            raise CollaborationServiceError("Falha ao executar o projeto.") from e

    def get_workspace_status(self) -> Dict[str, Any]:
        return collaboration_repository.get_workspace_status()

    def get_health_status(self) -> Dict[str, Any]:
        return collaboration_repository.get_system_health()


# Instância única do serviço
collaboration_service = CollaborationService()
