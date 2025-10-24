"""
Meta-Agent Cycle Worker

Consome mensagens da fila janus.meta_agent.cycle e dispara ciclos de análise
pontuais do Meta-Agente.
"""
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

from prometheus_client import Counter, Histogram

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import TaskMessage, QueueName

# Novas dependências para persistência de falhas em memória
from app.repositories.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService
from app.core.memory.memory_core import get_memory_db

logger = logging.getLogger(__name__)

# Métricas do worker Meta-Agente
_META_AGENT_MESSAGES_TOTAL = Counter(
    "meta_agent_messages_total",
    "Total de mensagens processadas pelo Meta-Agente",
    ["outcome", "mode"],
)
_META_AGENT_PROCESSING_SECONDS = Histogram(
    "meta_agent_processing_seconds",
    "Tempo de processamento de ciclos do Meta-Agente",
    ["mode"],
)

# Instância lazy para MemoryService (reutilizada entre handlers)
_memory_service: Optional[MemoryService] = None


async def _ensure_memory_initialized() -> None:
    global _memory_service
    if _memory_service is None:
        db = await get_memory_db()
        mem_repo = MemoryRepository(db)
        _memory_service = MemoryService(mem_repo)


@protect_against_poison_pills(
    queue_name=QueueName.META_AGENT_CYCLE.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_meta_agent_cycle(task: TaskMessage) -> None:
    """Processa uma mensagem para executar um ciclo de análise do meta-agente."""
    payload = task.payload or {}
    mode = payload.get("mode", "single")
    logger.info(
        f"Iniciando ciclo do meta-agente: task_id={task.task_id}, type={task.task_type}, mode={mode}"
    )
    start = time.perf_counter()
    try:
        from app.core.agents.meta_agent import get_meta_agent
        meta_agent = get_meta_agent()
        report = await meta_agent.run_analysis_cycle()

        duration = time.perf_counter() - start
        _META_AGENT_PROCESSING_SECONDS.labels(mode).observe(duration)
        _META_AGENT_MESSAGES_TOTAL.labels("success", mode).inc()
        logger.info(
            f"✓ Meta-Agente ciclo concluído (mode={mode}): status={report.overall_status}, duration={duration:.3f}s"
        )
    except Exception as e:
        _META_AGENT_MESSAGES_TOTAL.labels("error", mode).inc()
        logger.error(
            f"Erro no ciclo do meta-agente {task.task_id}: {e}",
            exc_info=True,
        )
        raise


async def publish_meta_agent_cycle(mode: str = "single", priority: int = 5) -> str:
    """Publica uma mensagem para disparar um ciclo do meta-agente.

    Prioridade padrão 5 (0-9). A fila deve possuir `x-max-priority`.
    """
    task_id = str(uuid.uuid4())
    payload: Dict[str, Any] = {"mode": mode}
    task_message = TaskMessage(
        task_id=task_id,
        task_type="meta_agent_cycle",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )

    serialized = task_message.model_dump_json()
    broker = await get_broker()
    await broker.publish(
        queue_name=QueueName.META_AGENT_CYCLE.value,
        message=serialized,
        priority=priority,
    )

    logger.info(f"Meta-Agente ciclo publicado: task_id={task_id}, mode={mode}, priority={priority}")
    return task_id


async def start_meta_agent_worker():
    """Inicia o consumidor da fila janus.meta_agent.cycle."""
    logger.info("Iniciando worker do Meta-Agente (ciclo)...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.META_AGENT_CYCLE.value,
        callback=process_meta_agent_cycle,
        prefetch_count=2,
    )
    logger.info("✓ Worker do Meta-Agente iniciado.")
    return consumer_task


# --- Consumidor orientado a eventos: falhas detectadas ---
@protect_against_poison_pills(
    queue_name=QueueName.FAILURE_DETECTED.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_failure_event(task: TaskMessage) -> None:
    """Consome eventos de falha (janus.failure.detected) e aciona uma análise do Meta-Agente.

    Também persiste um registro resumido na memória episódica para apoiar análises futuras.
    """
    await _ensure_memory_initialized()
    mode = "failure_event"
    start = time.perf_counter()
    try:
        payload = task.payload or {}
        reason = str(payload.get("reason", "unknown"))
        score = float(payload.get("score", 0.0) or 0.0)
        origin = str(payload.get("origin", "unknown"))
        context = payload.get("context", {}) or {}
        ts_iso = str(payload.get("timestamp", datetime.utcnow().isoformat()))

        # Persistir experiência de falha para análises posteriores
        assert _memory_service is not None
        meta = {
            "status": "failure",
            "error_type": reason,
            "component": origin,
            "score": score,
            "timestamp": ts_iso,
            "queue": QueueName.FAILURE_DETECTED.value,
            "task_id": task.task_id,
        }
        # Anexar contexto relevante se presente
        if isinstance(context, dict):
            meta.update({
                "conversation_id": context.get("conversation_id"),
                "interaction_id": context.get("interaction_id"),
                "task_preview": (context.get("task") or "")[:300],
            })
        await _memory_service.add_experience(
            type="action_failure",
            content=f"Failure detected: {reason}",
            metadata=meta,
        )

        # Disparar ciclo do Meta-Agente em background via fila dedicada
        await publish_meta_agent_cycle(mode=mode)

        duration = time.perf_counter() - start
        _META_AGENT_PROCESSING_SECONDS.labels(mode).observe(duration)
        _META_AGENT_MESSAGES_TOTAL.labels("success", mode).inc()
        logger.info(
            f"✓ Evento de falha processado pelo Meta-Agente: origin={origin}, reason={reason}, score={score:.2f}"
        )
    except Exception as e:
        _META_AGENT_MESSAGES_TOTAL.labels("error", mode).inc()
        logger.error(f"Erro ao processar evento de falha: {e}", exc_info=True)
        raise


async def start_failure_event_consumer():
    """Inicia o consumidor de eventos de falha (janus.failure.detected)."""
    logger.info("Iniciando consumidor de falhas do Meta-Agente (janus.failure.detected)...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.FAILURE_DETECTED.value,
        callback=process_failure_event,
        prefetch_count=5,
    )
    logger.info("✓ Consumidor de falhas do Meta-Agente iniciado.")
    return consumer_task