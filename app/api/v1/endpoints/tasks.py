import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.services.task_service import TaskService, get_task_service
from app.models.schemas import QueueName

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class ConsolidationTaskRequest(BaseModel):
    mode: str = Field("batch")
    limit: Optional[int] = Field(10)
    experience_id: Optional[str] = None
    experience_content: Optional[str] = None
    metadata: Optional[dict] = None

class TaskResponse(BaseModel):
    task_id: str
    message: str
    queue: str

class QueueInfoResponse(BaseModel):
    name: str
    messages: int
    consumers: int

# --- Endpoints ---

@router.post("/consolidation", response_model=TaskResponse, summary="Publica tarefa de consolidação")
async def create_consolidation_task(
        request: ConsolidationTaskRequest,
        service: TaskService = Depends(get_task_service)
):
    """Delega a publicação de uma tarefa de consolidação para o TaskService."""
    # TaskServiceError é tratado pelo exception handler central -> 500
    task_id = await service.create_consolidation_task(
        mode=request.mode,
        limit=request.limit,
        experience_id=request.experience_id,
        experience_content=request.experience_content,
        metadata=request.metadata
    )
    return TaskResponse(
        task_id=task_id,
        message=f"Tarefa de consolidação criada com sucesso (modo: {request.mode})",
        queue=QueueName.KNOWLEDGE_CONSOLIDATION
    )


@router.get("/queue/{queue_name}", response_model=QueueInfoResponse, summary="Obtém informações sobre uma fila")
async def get_queue_info(queue_name: str, service: TaskService = Depends(get_task_service)):
    """Delega a busca de informações da fila para o TaskService."""
    # TaskServiceError (se a fila não for encontrada) é tratado pelo handler -> 404
    info = await service.get_queue_details(queue_name)
    return QueueInfoResponse(**info)


@router.get("/health/rabbitmq", summary="Verifica saúde do RabbitMQ")
async def check_rabbitmq_health(service: TaskService = Depends(get_task_service)):
    """Delega a verificação de saúde do broker para o TaskService."""
    if await service.check_broker_health():
        return {"status": "healthy", "message": "Conexão com RabbitMQ está operacional"}

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="RabbitMQ não está acessível"
    )
