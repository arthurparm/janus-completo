import structlog
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.collaboration_service import (
    collaboration_service,
    CollaborationServiceError,
    AgentNotFoundError,
    TaskNotFoundError
)
from app.core.agents import AgentRole
from app.core.agents.multi_agent_system import TaskPriority, TaskStatus

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])
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
    assigned_to: Optional[str] = None
    priority: str = "medium"
    dependencies: List[str] = Field(default_factory=list)

class ExecuteTaskRequest(BaseModel):
    task_id: str
    agent_id: str

class ExecuteProjectRequest(BaseModel):
    description: str

# --- Endpoints ---

@router.post("/agents/create", response_model=CreateAgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: CreateAgentRequest):
    """Delega a criação de um novo agente para o CollaborationService."""
    try:
        role = AgentRole(request.role)
        agent = collaboration_service.create_agent(role)
        return CreateAgentResponse(
            agent_id=agent.agent_id,
            role=agent.role.value,
            message=f"Agente {role.value} criado com sucesso"
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Papel inválido: {request.role}")
    except CollaborationServiceError as e:
        logger.error("Erro no serviço de colaboração ao criar agente", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents", summary="Lista todos os agentes ativos")
async def list_agents():
    """Delega a listagem de agentes para o CollaborationService."""
    try:
        agents = collaboration_service.list_agents()
        return {"total_agents": len(agents), "agents": agents}
    except CollaborationServiceError as e:
        logger.error("Erro no serviço de colaboração ao listar agentes", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents/{agent_id}", summary="Obtém detalhes de um agente")
async def get_agent_details(agent_id: str):
    """Delega a busca de detalhes do agente para o CollaborationService."""
    try:
        return collaboration_service.get_agent_details(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CollaborationServiceError as e:
        logger.error("Erro no serviço ao buscar detalhes do agente", agent_id=agent_id, exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/tasks/create", summary="Cria uma nova tarefa")
async def create_task(request: CreateTaskRequest):
    """Delega a criação de uma tarefa para o CollaborationService."""
    try:
        priority = TaskPriority[request.priority.upper()]
        task = collaboration_service.create_task(
            description=request.description,
            priority=priority,
            assigned_to=request.assigned_to,
            dependencies=request.dependencies
        )
        return task.to_dict()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Prioridade inválida: {request.priority}")
    except CollaborationServiceError as e:
        logger.error("Erro no serviço ao criar tarefa", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/tasks/execute", summary="Executa uma tarefa específica")
async def execute_task(request: ExecuteTaskRequest):
    """Delega a execução de uma tarefa para o CollaborationService."""
    try:
        return await collaboration_service.execute_task(request.task_id, request.agent_id)
    except (AgentNotFoundError, TaskNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CollaborationServiceError as e:
        logger.error("Erro no serviço ao executar tarefa", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tasks", summary="Lista todas as tarefas")
async def list_tasks(status: Optional[str] = None):
    """Delega a listagem de tarefas para o CollaborationService."""
    try:
        task_status = TaskStatus(status) if status else None
        tasks = collaboration_service.list_tasks(task_status)
        return {"total_tasks": len(tasks), "tasks": [t.to_dict() for t in tasks]}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Status inválido: {status}")
    except CollaborationServiceError as e:
        logger.error("Erro no serviço ao listar tarefas", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tasks/{task_id}", summary="Obtém detalhes de uma tarefa")
async def get_task_details(task_id: str):
    """Delega a busca de detalhes da tarefa para o CollaborationService."""
    try:
        task = collaboration_service.get_task_details(task_id)
        return task.to_dict()
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/projects/execute", summary="Executa um projeto completo")
async def execute_project(request: ExecuteProjectRequest):
    """Delega a execução de um projeto para o CollaborationService."""
    try:
        return await collaboration_service.execute_project(request.description)
    except CollaborationServiceError as e:
        logger.error("Erro no serviço ao executar projeto", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/workspace/status", summary="Retorna o status do workspace")
async def get_workspace_status():
    """Delega a busca de status do workspace para o CollaborationService."""
    return collaboration_service.get_workspace_status()


@router.get("/health", summary="Health check do sistema de colaboração")
async def health_check():
    """Delega a verificação de saúde para o CollaborationService."""
    return collaboration_service.get_health_status()
