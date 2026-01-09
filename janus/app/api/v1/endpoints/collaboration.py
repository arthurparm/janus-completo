import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.agents import AgentRole
from app.services.collaboration_service import CollaborationService, get_collaboration_service

try:
    from app.core.agents.multi_agent_system import TaskPriority, TaskStatus
except Exception:
    from enum import Enum

    class TaskStatus(Enum):  # type: ignore
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        BLOCKED = "blocked"

    class TaskPriority(Enum):  # type: ignore
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        CRITICAL = 4


router = APIRouter(tags=["Collaboration"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class CreateAgentRequest(BaseModel):
    role: str


class CreateAgentResponse(BaseModel):
    agent_id: str
    role: str
    message: str


class CreateTaskRequest(BaseModel):
    description: str
    assigned_to: str | None = None
    priority: str = "medium"
    dependencies: list[str] = Field(default_factory=list)


class ExecuteTaskRequest(BaseModel):
    task_id: str
    agent_id: str


class ExecuteProjectRequest(BaseModel):
    description: str


class ExecuteTasksParallelRequest(BaseModel):
    task_ids: list[str] | None = Field(
        default=None,
        description="Lista de IDs de tarefas para executar; se vazio, executa todas PENDING",
    )
    concurrency: int = Field(default=4, ge=1, description="Limite de paralelismo")


# --- Endpoints ---


@router.post(
    "/agents/create", response_model=CreateAgentResponse, status_code=status.HTTP_201_CREATED
)
async def create_agent(
    request: CreateAgentRequest, service: CollaborationService = Depends(get_collaboration_service)
):
    """Delega a criação de um novo agente para o CollaborationService."""
    # ValueError é tratado pelo handler central -> 400
    role = AgentRole(request.role)
    agent_data = service.create_agent(role)
    return CreateAgentResponse(
        **agent_data, message=f"Agente {agent_data['role']} criado com sucesso"
    )


@router.get("/agents", summary="Lista todos os agentes ativos")
async def list_agents(service: CollaborationService = Depends(get_collaboration_service)):
    """Delega a listagem de agentes para o CollaborationService."""
    agents = service.list_agents()
    return {"total_agents": len(agents), "agents": agents}


@router.get("/agents/{agent_id}", summary="Obtém detalhes de um agente")
async def get_agent_details(
    agent_id: str, service: CollaborationService = Depends(get_collaboration_service)
):
    """Delega a busca de detalhes do agente para o CollaborationService."""
    # AgentNotFoundError é tratado pelo handler central -> 404
    return service.get_agent_details(agent_id)


@router.post("/tasks/create", summary="Cria uma nova tarefa")
async def create_task(
    request: CreateTaskRequest, service: CollaborationService = Depends(get_collaboration_service)
):
    """Delega a criação de uma tarefa para o CollaborationService."""
    try:
        priority = TaskPriority[request.priority.upper()]
        task = service.create_task(
            description=request.description,
            priority=priority,
            assigned_to=request.assigned_to,
            dependencies=request.dependencies,
        )
        return task.to_dict()
    except KeyError:  # Erro de validação de input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prioridade inválida: {request.priority}",
        )


@router.post("/tasks/execute", summary="Executa uma tarefa específica")
async def execute_task(
    request: ExecuteTaskRequest, service: CollaborationService = Depends(get_collaboration_service)
):
    """Delega a execução de uma tarefa para o CollaborationService."""
    # AgentNotFoundError e TaskNotFoundError são tratados pelo handler -> 404
    return await service.execute_task(request.task_id, request.agent_id)


@router.get("/tasks", summary="Lista todas as tarefas")
async def list_tasks(
    service: CollaborationService = Depends(get_collaboration_service), status: str | None = None
):
    """Delega a listagem de tarefas para o CollaborationService."""
    try:
        task_status = TaskStatus(status) if status else None
        tasks = service.list_tasks(task_status)
        return {"total_tasks": len(tasks), "tasks": [t.to_dict() for t in tasks]}
    except ValueError:  # Erro de validação de input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Status inválido: {status}"
        )


@router.get("/tasks/{task_id}", summary="Obtém detalhes de uma tarefa")
async def get_task_details(
    task_id: str, service: CollaborationService = Depends(get_collaboration_service)
):
    """Delega a busca de detalhes da tarefa para o CollaborationService."""
    # TaskNotFoundError é tratado pelo handler -> 404
    task = service.get_task_details(task_id)
    return task.to_dict()


@router.post("/projects/execute", summary="Executa um projeto completo")
async def execute_project(
    request: ExecuteProjectRequest,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Delega a execução de um projeto para o CollaborationService."""
    return await service.execute_project(request.description)


@router.get("/workspace/status", summary="Retorna o status do workspace")
async def get_workspace_status(service: CollaborationService = Depends(get_collaboration_service)):
    """Delega a busca de status do workspace para o CollaborationService."""
    return service.get_workspace_status()


@router.post(
    "/tasks/execute_parallel",
    summary="Executa múltiplas tarefas em paralelo respeitando dependências",
)
async def execute_tasks_parallel(
    request: ExecuteTasksParallelRequest,
    service: CollaborationService = Depends(get_collaboration_service),
):
    """Executa tarefas em paralelo, respeitando dependências entre elas.

    - Se `task_ids` não for fornecido, executa todas as tarefas PENDING no workspace.
    - `concurrency` limita o número de tarefas em execução simultânea.
    """
    return await service.execute_tasks_parallel(
        task_ids=request.task_ids, concurrency=request.concurrency
    )


@router.get("/health", summary="Health check do sistema de colaboração")
async def health_check(service: CollaborationService = Depends(get_collaboration_service)):
    """Delega a verificação de saúde para o CollaborationService."""
    return service.get_health_status()
