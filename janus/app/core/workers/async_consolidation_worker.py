"""
Async Knowledge Consolidation Worker - Sprint 1 + Sprint 8

Worker assíncrono que consome mensagens de consolidação de conhecimento do RabbitMQ.
Integra o Message Broker (Sprint 1) com o Knowledge Consolidator (Sprint 8).
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import msgpack

# Use broker getter to avoid None reference
from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
from app.models.schemas import QueueName, TaskMessage

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

            stats = await knowledge_consolidator.consolidate_batch(limit=limit, min_score=min_score)

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
                raise ValueError(
                    "experience_id e experience_content são obrigatórios para modo 'single'"
                )

            result = await knowledge_consolidator.consolidate_experience(
                experience_id=experience_id,
                experience_content=experience_content,
                metadata=metadata,
            )

            logger.info(
                f"✓ Consolidação individual concluída: {result['entities_created']} entidades, "
                f"{result['relationships_created']} relacionamentos criados."
            )

            # --- Notificação de Evento para o Chat HUD ---
            try:
                # Se algo foi criado, avisa o frontend
                if result["entities_created"] > 0 or result["relationships_created"] > 0:
                    conversation_id = metadata.get("conversation_id")
                    if conversation_id:
                        broker = await get_broker()

                        # Extrai nomes das entidades para mostrar no HUD
                        # O result nao retorna os nomes, entao vamos fazer uma estimativa ou
                        # modificar o consolidator para retornar nomes.
                        # Por simplicidade, vamos mandar uma mensagem generica por enquanto
                        # ou tentar pegar do conteudo se for curto.

                        # Melhor: Vamos assumir que foi "Memória consolidada com sucesso"
                        # Idealmente o consolidator retornaria os nomes das entidades.
                        # Mas vamos mandar o evento.

                        event_payload = {
                            "event_type": "memory_consolidated",
                            "agent_role": "knowledge_curator",
                            "content": f"Memória consolidada: {result['entities_created']} novas entidades conectadas.",
                            "timestamp": datetime.utcnow().timestamp(),
                            "task_id": task.task_id,
                            "metadata": {
                                "entities_count": result["entities_created"],
                                "relationships_count": result["relationships_created"],
                            },
                        }

                        # Routing key para a conversa específica
                        routing_key = f"janus.event.conversation.{conversation_id}.memory"

                        await broker.publish(
                            exchange_name="janus.events",
                            routing_key=routing_key,
                            message=msgpack.packb(event_payload, use_bin_type=True),
                            use_msgpack=False,  # Já empacotamos manualmente
                        )
                        logger.debug(f"Evento de memória publicado para {conversation_id}")
            except Exception as evt_err:
                logger.warning(f"Falha ao publicar evento de memória: {evt_err}")

        else:
            raise ValueError(f"Modo de consolidação desconhecido: {consolidation_mode}")

    except Exception as e:
        logger.error(f"Erro ao processar tarefa de consolidação {task.task_id}: {e}", exc_info=True)
        raise


async def publish_consolidation_task(
    payload: dict[str, Any], correlation_id: str | None = None
) -> dict[str, Any]:
    """Publica uma tarefa de consolidação na fila apropriada."""
    broker = await get_broker()
    # Alinha com o esquema de TaskMessage (timestamp obrigatório) e serializa
    task_message = TaskMessage(
        task_id=str(uuid.uuid4()),
        task_type="knowledge_consolidation",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )
    serialized = msgpack.packb(task_message.model_dump(), use_bin_type=True)
    await broker.publish(
        queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value, message=serialized, use_msgpack=True
    )
    return {"status": "ok", "task_id": task_message.task_id}


async def start_consolidation_worker():
    """
    Inicia o worker de consolidação de conhecimento.
    Consome mensagens da fila de consolidação e processa em background.
    """
    logger.info("Iniciando worker de consolidação de conhecimento...")

    broker = await get_broker()

    # Inicia o consolidator com await (método assíncrono)
    await knowledge_consolidator._initialize()

    # Inicia consumidor da fila
    # Reduzido prefetch_count para 2 para mitigar latência no LLM (evitar starvation de requisições interativas)
    # Originalmente 5, mas com backlog alto, isso pode saturar o Ollama.
    consumer_task = broker.start_consumer(
        queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
        callback=process_consolidation_task,
        prefetch_count=2,
    )

    logger.info("✓ Worker de consolidação de conhecimento iniciado.")

    return consumer_task
