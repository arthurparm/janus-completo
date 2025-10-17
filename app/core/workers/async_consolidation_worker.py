"""
Async Knowledge Consolidation Worker - Sprint 1 + Sprint 8

Worker assíncrono que consome mensagens de consolidação de conhecimento do RabbitMQ.
Integra o Message Broker (Sprint 1) com o Knowledge Consolidator (Sprint 8).
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

# Use broker getter to avoid None reference
from app.core.infrastructure.message_broker import get_broker
from app.models.schemas import TaskMessage, QueueName
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills

logger = logging.getLogger(__name__)


@protect_against_poison_pills(
    queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_consolidation_task(task: TaskMessage) -> None:
    """
    Processa uma tarefa de consolidação de conhecimento recebida do RabbitMQ.

    Args:
        task: Mensagem de tarefa recebida
    """
    logger.info(
        f"Iniciando processamento de tarefa de consolidação: "
        f"task_id={task.task_id}, type={task.task_type}"
    )

    try:
        payload = task.payload
        consolidation_mode = payload.get("mode", "batch")

        if consolidation_mode == "batch":
            # Consolidação em lote
            limit = payload.get("limit", 10)
            min_score = payload.get("min_score", 0.0)

            stats = await knowledge_consolidator.consolidate_batch(
                limit=limit,
                min_score=min_score
            )

            logger.info(
                f"✓ Consolidação em lote concluída: {stats['successful']}/{stats['total_processed']} "
                f"experiências processadas, {stats['total_entities']} entidades, "
                f"{stats['total_relationships']} relacionamentos criados."
            )

        elif consolidation_mode == "single":
            # Consolidação de uma única experiência
            experience_id = payload.get("experience_id")
            experience_content = payload.get("experience_content")
            metadata = payload.get("metadata", {})

            if not experience_id or not experience_content:
                raise ValueError("experience_id e experience_content são obrigatórios para modo 'single'")

            result = await knowledge_consolidator.consolidate_experience(
                experience_id=experience_id,
                experience_content=experience_content,
                metadata=metadata
            )

            logger.info(
                f"✓ Consolidação individual concluída: {result['entities_created']} entidades, "
                f"{result['relationships_created']} relacionamentos criados."
            )

        else:
            raise ValueError(f"Modo de consolidação desconhecido: {consolidation_mode}")

    except Exception as e:
        logger.error(
            f"Erro ao processar tarefa de consolidação {task.task_id}: {e}",
            exc_info=True
        )
        raise


async def publish_consolidation_task(
        mode: str = "batch",
        limit: int = 10,
        experience_id: str = None,
        experience_content: str = None,
        metadata: Dict[str, Any] = None
) -> str:
    """
    Publica uma tarefa de consolidação no RabbitMQ.

    Args:
        mode: Modo de consolidação ("batch" ou "single")
        limit: Limite de experiências (para modo batch)
        experience_id: ID da experiência (para modo single)
        experience_content: Conteúdo da experiência (para modo single)
        metadata: Metadados da experiência (para modo single)

    Returns:
        ID da tarefa publicada
    """
    task_id = str(uuid.uuid4())

    payload = {
        "mode": mode,
        "limit": limit if mode == "batch" else None,
        "experience_id": experience_id if mode == "single" else None,
        "experience_content": experience_content if mode == "single" else None,
        "metadata": metadata if mode == "single" else None
    }

    task_message = TaskMessage(
        task_id=task_id,
        task_type="knowledge_consolidation",
        payload=payload,
        timestamp=datetime.utcnow().timestamp()
    )

    # Ensure message is serialized to JSON string for broker compatibility
    serialized = task_message.model_dump_json()
    broker = await get_broker()
    await broker.publish(
        queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
        message=serialized
    )

    logger.info(f"Tarefa de consolidação publicada: task_id={task_id}, mode={mode}")

    return task_id


async def start_consolidation_worker():
    """
    Inicia o worker de consolidação de conhecimento.
    Consome mensagens da fila de consolidação e processa em background.
    """
    logger.info("Iniciando worker de consolidação de conhecimento...")

    broker = await get_broker()

    # Inicia o consolidator
    knowledge_consolidator._initialize()

    # Inicia consumidor da fila
    consumer_task = broker.start_consumer(
        queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
        callback=process_consolidation_task,
        prefetch_count=5  # Processa até 5 tarefas em paralelo
    )

    logger.info("✓ Worker de consolidação de conhecimento iniciado.")

    return consumer_task
