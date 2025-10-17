import structlog
from typing import Dict, Any, List, Optional
from fastapi import Request

from app.repositories.collaboration_repository import CollaborationRepository, CollaborationRepositoryError
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


class AgentNotFoundError(CollaborationServiceError):
    """Raised when an agent is not found."""
    pass

# --- Collaboration Service ---

class CollaborationService:
    """
    Camada de serviço para o sistema de colaboração multi-agente.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: CollaborationRepository):
        self._repo = repo

    def create_agent(self, role: AgentRole) -> Dict[str, Any]:
        logger.info("Orquestrando criação de agente via serviço", role=role.value)
        agent = self._repo.create_agent(role)
        return {"agent_id": agent.agent_id, "role": agent.role.value}

    def list_agents(self) -> List[Dict[str, Any]]:
        logger.info("Orquestrando listagem de agentes via serviço")
        return self._repo.find_all_agents()

    def get_agent_details(self, agent_id: str) -> Dict[str, Any]:
        logger.info("Orquestrando busca de detalhes do agente", agent_id=agent_id)
        agent = self._repo.find_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")

        tasks = self._repo.find_tasks_by_agent(agent_id)
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
        self._repo.save_task(task)
        return task

    async def execute_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        logger.info("Orquestrando execução de tarefa via serviço", task_id=task_id, agent_id=agent_id)
        agent = self._repo.find_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")
        task = self._repo.find_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Tarefa '{task_id}' não encontrada.")
        return await self._repo.run_task(agent, task)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        logger.info("Orquestrando listagem de tarefas via serviço", status=status)
        if status:
            return self._repo.find_tasks_by_status(status)
        return self._repo.find_all_tasks()

    def get_task_details(self, task_id: str) -> Task:
        logger.info("Orquestrando busca de detalhes da tarefa", task_id=task_id)
        task = self._repo.find_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Tarefa '{task_id}' não encontrada.")
        return task

    async def execute_project(self, description: str) -> Dict[str, Any]:
        logger.info("Orquestrando execução de projeto via serviço", project_description=description)
        try:
            return await self._repo.run_project(description)
        except Exception as e:
            logger.error("Erro no repositório ao executar projeto", exc_info=e)
            raise CollaborationServiceError("Falha ao executar o projeto.") from e

    def get_workspace_status(self) -> Dict[str, Any]:
        return self._repo.get_workspace_status()

    def get_health_status(self) -> Dict[str, Any]:
        return self._repo.get_system_health()

    # --- Shared Workspace Operations ---
    def add_artifact(self, key: str, value: Any, author: str) -> Dict[str, Any]:
        logger.info("Orquestrando adição de artefato ao workspace", key=key, author=author)
        # Validar agente autor, se fornecido
        if author:
            agent = self._repo.find_agent_by_id(author)
            if not agent:
                raise AgentNotFoundError(f"Agente '{author}' não encontrado.")
        self._repo.add_artifact(key, value, author)
        return {"key": key, "author": author}

    def get_artifact(self, key: str) -> Optional[Any]:
        logger.info("Orquestrando leitura de artefato do workspace", key=key)
        return self._repo.get_artifact(key)

    def send_message(self, from_agent: str, to_agent: str, content: str) -> Dict[str, Any]:
        logger.info("Orquestrando envio de mensagem entre agentes", from_agent=from_agent, to_agent=to_agent)
        # Validar agentes
        if not self._repo.find_agent_by_id(from_agent):
            raise AgentNotFoundError(f"Agente '{from_agent}' não encontrado.")
        if not self._repo.find_agent_by_id(to_agent):
            raise AgentNotFoundError(f"Agente '{to_agent}' não encontrado.")
        return self._repo.send_message(from_agent, to_agent, content)

    def get_messages_for(self, agent_id: str) -> List[Dict[str, Any]]:
        logger.info("Orquestrando recuperação de mensagens para agente", agent_id=agent_id)
        # Validar agente
        if not self._repo.find_agent_by_id(agent_id):
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")
        return self._repo.get_messages_for(agent_id)

    # --- System Control ---
    def shutdown_system(self) -> None:
        logger.info("Orquestrando desligamento do sistema multi-agente")
        self._repo.shutdown_all()

    # --- Parallel Execution ---
    async def execute_tasks_parallel(self, task_ids: Optional[List[str]] = None, concurrency: int = 4) -> Dict[
        str, Any]:
        """Exposição de execução paralela com dependências via serviço."""
        logger.info("Orquestrando execução paralela de tarefas", task_ids=task_ids, concurrency=concurrency)
        try:
            return await self._repo.run_tasks_parallel(task_ids=task_ids, concurrency=concurrency)
        except Exception as e:
            logger.error("Erro ao executar tarefas em paralelo", exc_info=e)
            raise CollaborationServiceError("Falha na execução paralela de tarefas.") from e

# Padrão de Injeção de Dependência: Getter para o serviço
def get_collaboration_service(request: Request) -> CollaborationService:
    return request.app.state.collaboration_service
