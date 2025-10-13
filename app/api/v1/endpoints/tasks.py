import structlog
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.task_service import task_service, TaskServiceError

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class ConsolidationTaskRequest(BaseModel):
    mode: str = Field("batch", description="Modo: 'batch' ou 'single'")
    limit: Optional[int] = Field(10, description="Limite de experiências (modo batch)")
    experience_id: Optional[str] = Field(None, description="ID da experiência (modo single)")
    experience_content: Optional[str] = Field(None, description="Conteúdo (modo single)")
    metadata: Optional[dict] = Field(None, description="Metadados (modo single)")

class TaskResponse(BaseModel):
    task_id: str
    message: str
    queue: str

class QueueInfoResponse(BaseModel):
    name: str
    messages: int
    consumers: int


# --- Endpoints ---

@router.post(
    "/consolidation",
    response_model=TaskResponse,
    summary="Publica tarefa de consolidação de conhecimento",
    tags=["Tasks"]
)
async def create_consolidation_task(request: ConsolidationTaskRequest):
    """Delega a publicação de uma tarefa de consolidação para o TaskService."""
    try:
        task_id = await task_service.create_consolidation_task(
            mode=request.mode,
            limit=request.limit,
            experience_id=request.experience_id,
            experience_content=request.experience_content,
            metadata=request.metadata
        )
        return TaskResponse(
            task_id=task_id,
            message=f"Tarefa de consolidação criada com sucesso (modo: {request.mode})",
            queue="janus.knowledge.consolidation"
        )
    except TaskServiceError as e:
        logger.error("Erro no serviço de tarefas ao criar tarefa de consolidação", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/queue/{queue_name}",
    response_model=QueueInfoResponse,
    summary="Obtém informações sobre uma fila",
    tags=["Tasks"]
)
async def get_queue_info(queue_name: str):
    """Delega a busca de informações da fila para o TaskService."""
    try:
        info = await task_service.get_queue_details(queue_name)
        return QueueInfoResponse(
            name=info["name"],
            messages=info["messages"],
            consumers=info["consumers"]
        )
    except TaskServiceError as e:
        logger.error("Erro no serviço de tarefas ao buscar informações da fila", queue_name=queue_name, exc_info=e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/health/rabbitmq",
    summary="Verifica saúde do RabbitMQ",
    tags=["Tasks"]
)
async def check_rabbitmq_health():
    """Delega a verificação de saúde do broker para o TaskService."""
    is_healthy = await task_service.check_broker_health()
    if is_healthy:
        return {
            "status": "healthy",
            "message": "Conexão com RabbitMQ está operacional"
        }
    else:
        logger.warning("Health check do RabbitMQ falhou.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RabbitMQ não está acessível"
        )
