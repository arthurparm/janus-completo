import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import Request

from app.core.agents import AgentRole
from app.repositories.collaboration_repository import (
    CollaborationRepository,
)

from app.core.agents.structures import Task, TaskPriority, TaskStatus


from app.core.infrastructure.context_cache import get_context_cache
from app.core.infrastructure.message_broker import get_broker
from app.models.schemas import QueueName, TaskMessage, TaskState

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
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: CollaborationRepository):
        self._repo = repo

    async def create_agent(self, role: AgentRole) -> dict[str, Any]:
        logger.info("Orquestrando criação de agente via serviço", role=role.value)
        agent = await self._repo.create_agent(role)
        return {"agent_id": agent.agent_id, "role": agent.role.value}

    def list_agents(self) -> list[dict[str, Any]]:
        logger.info("Orquestrando listagem de agentes via serviço")
        return self._repo.find_all_agents()

    def get_agent_details(self, agent_id: str) -> dict[str, Any]:
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
                status.value: len([t for t in tasks if t.status == status]) for status in TaskStatus
            },
        }

    def create_task(
        self,
        description: str,
        priority: TaskPriority,
        assigned_to: str | None,
        dependencies: list[str],
    ) -> Task:
        logger.info("Orquestrando criação de tarefa via serviço", description=description)
        task = Task(
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            dependencies=dependencies,
        )
        self._repo.save_task(task)
        return task

    async def execute_task(self, task_id: str, agent_id: str) -> dict[str, Any]:
        logger.info(
            "Orquestrando execução de tarefa via serviço", task_id=task_id, agent_id=agent_id
        )
        agent = self._repo.find_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agente '{agent_id}' não encontrado.")
        task = self._repo.find_task_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Tarefa '{task_id}' não encontrada.")
        return await self._repo.run_task(agent, task)

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
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

    async def execute_project(self, description: str) -> dict[str, Any]:
        logger.info("Orquestrando execução de projeto via serviço", project_description=description)
        try:
            return await self._repo.run_project(description)
        except Exception as e:
            logger.error("Erro no repositório ao executar projeto", exc_info=e)
            raise CollaborationServiceError("Falha ao executar o projeto.") from e

    def get_workspace_status(self) -> dict[str, Any]:
        return self._repo.get_workspace_status()

    def get_health_status(self) -> dict[str, Any]:
        return self._repo.get_system_health()

    # --- Shared Workspace Operations ---
    def add_artifact(self, key: str, value: Any, author: str) -> dict[str, Any]:
        logger.info("Orquestrando adição de artefato ao workspace", key=key, author=author)
        # Validar agente autor, se fornecido
        if author:
            agent = self._repo.find_agent_by_id(author)
            if not agent:
                raise AgentNotFoundError(f"Agente '{author}' não encontrado.")
        self._repo.add_artifact(key, value, author)
        return {"key": key, "author": author}

    def get_artifact(self, key: str) -> Any | None:
        logger.info("Orquestrando leitura de artefato do workspace", key=key)
        return self._repo.get_artifact(key)

    def send_message(self, from_agent: str, to_agent: str, content: str) -> dict[str, Any]:
        logger.info(
            "Orquestrando envio de mensagem entre agentes", from_agent=from_agent, to_agent=to_agent
        )
        # Validar agentes
        if not self._repo.find_agent_by_id(from_agent):
            raise AgentNotFoundError(f"Agente '{from_agent}' não encontrado.")
        if not self._repo.find_agent_by_id(to_agent):
            raise AgentNotFoundError(f"Agente '{to_agent}' não encontrado.")
        return self._repo.send_message(from_agent, to_agent, content)

    def get_messages_for(self, agent_id: str) -> list[dict[str, Any]]:
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
    async def execute_tasks_parallel(
        self, task_ids: list[str] | None = None, concurrency: int = 4
    ) -> dict[str, Any]:
        """Exposição de execução paralela com dependências via serviço."""
        logger.info(
            "Orquestrando execução paralela de tarefas", task_ids=task_ids, concurrency=concurrency
        )
        try:
            return await self._repo.run_tasks_parallel(task_ids=task_ids, concurrency=concurrency)
        except Exception as e:
            logger.error("Erro ao executar tarefas em paralelo", exc_info=e)
            raise CollaborationServiceError("Falha na execução paralela de tarefas.") from e

    # --- Parliament Routing ---
    async def pass_task(self, task_state: TaskState) -> str:
        """
        Publica o TaskState na fila adequada com base em `next_agent_role`.
        Fallback: roteia para `JANUS.tasks.router` quando indefinido.

        Stateful Workers: If context not cached, store static context and set flag.
        """
        # Stateful Workers: Cache static context on first hop
        if not task_state.context_cached:
            cache = get_context_cache()
            static_context = {
                "original_goal": task_state.original_goal,
                "meta": task_state.meta,
            }
            context_hash = cache.store(task_state.task_id, static_context)
            task_state.context_cached = True
            task_state.static_context_hash = context_hash
            logger.debug("Static context cached for task", task_id=task_state.task_id)

        role = (task_state.next_agent_role or "router").lower()
        # Mapear filas por papel
        if role in ("coder", "code", "code_agent"):
            queue = QueueName.TASKS_AGENT_CODER.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        elif role in ("professor", "review", "professor_agent", "curator"):
            queue = QueueName.TASKS_AGENT_PROFESSOR.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        elif role in ("sandbox", "tester", "test"):
            queue = QueueName.TASKS_AGENT_SANDBOX.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        elif role in ("red_team", "security", "auditor"):
            queue = QueueName.TASKS_AGENT_RED_TEAM.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        elif role in ("thinker", "thinker_agent", "architect", "reasoning"):
            queue = QueueName.TASKS_AGENT_THINKER.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        elif role in ("knowledge_consolidator", "knowledge", "consolidator", "librarian", "memory"):
            # Publicação especial para o pipeline de consolidação
            queue = QueueName.KNOWLEDGE_CONSOLIDATION.value
            payload = task_state.data_payload or {}
            content = payload.get("tool_output") or payload.get("sandbox_output") or ""
            # Se não houver conteúdo, usa o objetivo para não perder o ciclo
            if not content:
                content = task_state.original_goal or ""
            # Agente de origem
            origin_agent = None
            try:
                # último evento diferente de router
                for ev in reversed(task_state.history):
                    ar = ev.get("agent_role")
                    if ar and ar != "router":
                        origin_agent = ar
                        break
            except Exception as e:
                logger.warning(f"Falha ao determinar agente de origem: {e}")
                origin_agent = None
            meta = {
                "source_task_id": task_state.task_id,
                "original_goal": task_state.original_goal,
                "origin": "router",
                "source_agent": origin_agent,
                "status": task_state.status,
                "timestamp": datetime.utcnow().isoformat(),
            }
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="knowledge_consolidation",
                payload={
                    "mode": "single",
                    "experience_id": task_state.task_id,  # usa o id da tarefa como experiência agregadora
                    "experience_content": content,
                    "metadata": meta,
                },
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()
        else:
            queue = QueueName.TASKS_ROUTER.value
            msg = TaskMessage(
                task_id=task_state.task_id,
                task_type="task_state",
                payload={"task_state": task_state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump_json()

        broker = await get_broker()
        await broker.publish(queue_name=queue, message=msg)
        logger.info("TaskState publicado", queue=queue, task_id=task_state.task_id, next_role=role)
        return queue


# Padrão de Injeção de Dependência: Getter para o serviço
def get_collaboration_service(request: Request) -> CollaborationService:
    return request.app.state.collaboration_service
