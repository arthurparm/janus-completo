"""
Async Knowledge Consolidation Worker - Sprint 1 + Sprint 8

Worker assíncrono que consome mensagens de consolidação de conhecimento do RabbitMQ.
Integra o Message Broker (Sprint 1) com o Knowledge Consolidator (Sprint 8).
"""
import structlog
import uuid
from datetime import UTC, datetime
from typing import Any

try:
    import msgpack
except Exception:
    import json as _json

    class _MsgPackCompat:
        @staticmethod
        def packb(obj: Any, use_bin_type: bool = True) -> bytes:
            del use_bin_type
            return _json.dumps(obj, ensure_ascii=False).encode("utf-8")

        @staticmethod
        def unpackb(data: bytes | bytearray, raw: bool = False):
            del raw
            if isinstance(data, (bytes, bytearray)):
                return _json.loads(data.decode("utf-8"))
            return _json.loads(str(data))

    msgpack = _MsgPackCompat()  # type: ignore[assignment]

# Use broker getter to avoid None reference
from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
from app.models.schemas import QueueName, TaskMessage

logger = structlog.get_logger(__name__)


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
    logger.info("log_info", message=f"Iniciando processamento de tarefa de consolidação: "
        f"task_id={task.task_id}, type={task.task_type}"
    )

    payload = task.payload
    consolidation_mode = payload.get("mode", "batch")

    try:
        if consolidation_mode == "batch":
            # Consolidação em lote
            limit = payload.get("limit", 10)
            min_score = payload.get("min_score", 0.0)

            stats = await knowledge_consolidator.consolidate_batch(limit=limit, min_score=min_score)

            logger.info("log_info", message=f"✓ Consolidação em lote concluída: {stats['successful']}/{stats['total_processed']} "
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

            logger.info("log_info", message=f"✓ Consolidação individual concluída: {result['entities_created']} entidades, "
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
                            "timestamp": datetime.now(UTC).timestamp(),
                            "task_id": task.task_id,
                            "metadata": {
                                "entities_count": result["entities_created"],
                                "relationships_count": result["relationships_created"],
                            },
                        }

                        # Routing key para a conversa específica
                        routing_key = f"janus.event.conversation.{conversation_id}.memory"

                        await broker.publish_to_exchange(
                            exchange_name="janus.events",
                            routing_key=routing_key,
                            message=msgpack.packb(event_payload, use_bin_type=True),
                        )
                        logger.debug("log_debug", message=f"Evento de memória publicado para {conversation_id}")
            except Exception as evt_err:
                logger.warning("log_warning", message=f"Falha ao publicar evento de memória: {evt_err}")

        elif consolidation_mode == "knowledge_space":
            from app.core.kernel import Kernel
            from app.services.knowledge_space_service import KnowledgeSpaceService

            knowledge_space_id = str(payload.get("knowledge_space_id") or "").strip()
            limit_docs = int(payload.get("limit_docs", 20) or 20)
            if not knowledge_space_id:
                raise ValueError(
                    "knowledge_space_id é obrigatório para modo 'knowledge_space'"
                )

            kernel = Kernel.get_instance()
            result = await KnowledgeSpaceService(
                manifest_repo=getattr(kernel, "document_manifest_repo", None),
                llm_service=getattr(kernel, "llm_service", None),
            ).consolidate_space(
                knowledge_space_id=knowledge_space_id,
                limit_docs=limit_docs,
            )

            logger.info(
                "log_info",
                message=(
                    "✓ Consolidação estrutural do knowledge space concluída: "
                    f"{result['documents_total']} documento(s), {result['sections_total']} seção(ões)."
                ),
            )

        else:
            raise ValueError(f"Modo de consolidação desconhecido: {consolidation_mode}")

    except Exception as e:
        if consolidation_mode == "knowledge_space":
            knowledge_space_id = str(payload.get("knowledge_space_id") or "").strip()
            if knowledge_space_id:
                try:
                    from app.services.knowledge_space_service import KnowledgeSpaceService

                    KnowledgeSpaceService()._space_repo.mark_consolidation(
                        knowledge_space_id,
                        status="failed",
                        summary=f"Falha na consolidação estrutural: {e}",
                    )
                except Exception:
                    logger.warning(
                        "log_warning",
                        message=(
                            "Não foi possível marcar o knowledge space como failed após erro "
                            f"na tarefa {task.task_id}."
                        ),
                    )
        logger.error("log_error", message=f"Erro ao processar tarefa de consolidação {task.task_id}: {e}", exc_info=True)
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
        timestamp=datetime.now(UTC).timestamp(),
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
