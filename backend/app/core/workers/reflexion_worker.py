"""
Reflexion Worker - Consome tarefas de reflexão e publica sinais de falha.

Liga a fila interna "janus.tasks.reflexion" ao serviço de Reflexion.
Quando detectar falha ou baixa eficiência, publica "janus.failure.detected".
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from app.config import settings
from app.core.infrastructure.message_broker import get_broker
from app.core.memory.memory_core import get_memory_db
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage
from app.repositories.memory_repository import MemoryRepository
from app.repositories.reflexion_repository import ReflexionRepository
from app.services.memory_service import MemoryService
from app.services.reflexion_service import ReflexionService

logger = logging.getLogger(__name__)

# Instâncias lazy (criadas em start_reflexion_worker)
_memory_service: MemoryService | None = None
_reflexion_service: ReflexionService | None = None


async def _ensure_services_initialized() -> None:
    global _memory_service, _reflexion_service
    if _memory_service is None:
        db = await get_memory_db()
        mem_repo = MemoryRepository(db)
        _memory_service = MemoryService(mem_repo)
    if _reflexion_service is None:
        repo = ReflexionRepository(memory_service=_memory_service)
        _reflexion_service = ReflexionService(repo=repo)


async def publish_reflexion_task(
    payload: dict[str, Any], correlation_id: str | None = None
) -> dict[str, Any]:
    """Publica uma tarefa de Reflexion na fila interna."""
    broker = await get_broker()
    task_message = TaskMessage(
        task_id=str(uuid.uuid4()),
        task_type="reflexion_task",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )
    await broker.publish(
        queue_name=QueueName.REFLEXION_TASKS.value,
        message=task_message.model_dump_json(),
        priority=5,
        headers={"correlation_id": correlation_id} if correlation_id else None,
    )
    return {"status": "ok", "task_id": task_message.task_id}


async def _publish_failure_signal(reason: str, score: float, context: dict[str, Any]) -> None:
    broker = await get_broker()
    failure_payload = {
        "reason": reason,
        "score": score,
        "context": context,
        "timestamp": datetime.utcnow().isoformat(),
        "origin": "reflexion_worker",
    }
    msg = TaskMessage(
        task_id=str(uuid.uuid4()),
        task_type="failure_detected",
        payload=failure_payload,
        timestamp=datetime.utcnow().timestamp(),
    )
    await broker.publish(
        queue_name=QueueName.FAILURE_DETECTED.value,
        message=msg.model_dump_json(),
        priority=10,
    )


@protect_against_poison_pills(
    queue_name=QueueName.REFLEXION_TASKS.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_reflexion_task(task: TaskMessage) -> None:
    """Processa uma tarefa de Reflexion recebida da fila."""
    await _ensure_services_initialized()
    assert _reflexion_service is not None

    payload = task.payload or {}
    task_text = payload.get("task") or payload.get("prompt") or ""
    interaction_id = payload.get("interaction_id")
    conversation_id = payload.get("conversation_id")
    overrides: dict[str, Any] = payload.get("config_overrides", {})

    if not task_text:
        logger.warning(f"Tarefa de Reflexion vazia. task_id={task.task_id}")
        return

    logger.info(
        f"Reflexion: iniciando ciclo para task_id={task.task_id} interaction_id={interaction_id}"
    )

    try:
        result = await _reflexion_service.run_reflexion_cycle(
            task=task_text, config_overrides=overrides
        )
        success = bool(result.get("success", False))
        best_score = float(result.get("best_score", 0.0))
        lessons = result.get("lessons_learned", [])

        logger.info(
            f"Reflexion concluído: success={success} best_score={best_score:.2f} lessons={len(lessons)}"
        )

        threshold = overrides.get("success_threshold") or settings.REFLEXION_SUCCESS_THRESHOLD
        if not success or best_score < float(threshold):
            reason = "Reflexion abaixo do limiar" if success is False else "Score insuficiente"
            await _publish_failure_signal(
                reason=reason,
                score=best_score,
                context={
                    "interaction_id": interaction_id,
                    "conversation_id": conversation_id,
                    "task": task_text[:500],
                },
            )

    except Exception as e:
        logger.error(f"Erro ao executar Reflexion: {e}", exc_info=True)
        # Publica falha crítica imediatamente
        await _publish_failure_signal(
            reason=f"Reflexion error: {e}",
            score=0.0,
            context={
                "interaction_id": interaction_id,
                "conversation_id": conversation_id,
                "task": task_text[:500],
            },
        )
        raise


async def start_reflexion_worker():
    """Inicia o consumidor da fila de Reflexion."""
    await _ensure_services_initialized()
    broker = await get_broker()
    logger.info("Iniciando worker de Reflexion (janus.tasks.reflexion)...")
    consumer_task = broker.start_consumer(
        queue_name=QueueName.REFLEXION_TASKS.value,
        callback=process_reflexion_task,
        prefetch_count=3,
    )
    logger.info("✓ Worker de Reflexion iniciado.")
    return consumer_task
