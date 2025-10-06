"""
Endpoints para gerenciamento de tarefas assíncronas - Sprint 1

Permite publicar e monitorar tarefas no message broker (RabbitMQ).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.infrastructure import message_broker
from app.core.workers import publish_consolidation_task

router = APIRouter()
logger = logging.getLogger(__name__)


class ConsolidationTaskRequest(BaseModel):
    """Request para criar tarefa de consolidação de conhecimento."""
    mode: str = Field("batch", description="Modo: 'batch' ou 'single'")
    limit: Optional[int] = Field(10, description="Limite de experiências (modo batch)")
    experience_id: Optional[str] = Field(None, description="ID da experiência (modo single)")
    experience_content: Optional[str] = Field(None, description="Conteúdo (modo single)")
    metadata: Optional[dict] = Field(None, description="Metadados (modo single)")


class TaskResponse(BaseModel):
    """Response genérica de tarefa."""
    task_id: str
    message: str
    queue: str


class QueueInfoResponse(BaseModel):
    """Informações sobre uma fila."""
    name: str
    messages: int
    consumers: int


@router.post(
    "/consolidation",
    response_model=TaskResponse,
    summary="Publica tarefa de consolidação de conhecimento",
    tags=["Tasks"]
)
async def create_consolidation_task(request: ConsolidationTaskRequest):
    """
    Publica uma tarefa de consolidação de conhecimento no RabbitMQ.

    A tarefa será processada de forma assíncrona por um worker dedicado.

    **Modo batch**: Consolida múltiplas experiências da memória episódica
    **Modo single**: Consolida uma experiência específica
    """
    try:
        task_id = await publish_consolidation_task(
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

    except Exception as e:
        logger.error(f"Erro ao criar tarefa de consolidação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/queue/{queue_name}",
    response_model=QueueInfoResponse,
    summary="Obtém informações sobre uma fila",
    tags=["Tasks"]
)
async def get_queue_info(queue_name: str):
    """
    Retorna informações sobre uma fila específica do RabbitMQ.

    Inclui:
    - Número de mensagens na fila
    - Número de consumidores ativos
    """
    try:
        info = await message_broker.get_queue_info(queue_name)

        return QueueInfoResponse(
            name=info["name"],
            messages=info["messages"],
            consumers=info["consumers"]
        )

    except Exception as e:
        logger.error(f"Erro ao obter informações da fila {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health/rabbitmq",
    summary="Verifica saúde do RabbitMQ",
    tags=["Tasks"]
)
async def check_rabbitmq_health():
    """
    Verifica se a conexão com RabbitMQ está saudável.
    """
    try:
        is_healthy = await message_broker.health_check()

        if is_healthy:
            return {
                "status": "healthy",
                "message": "Conexão com RabbitMQ está operacional"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="RabbitMQ não está acessível"
            )

    except Exception as e:
        logger.error(f"Erro no health check do RabbitMQ: {e}")
        raise HTTPException(status_code=503, detail=str(e))
