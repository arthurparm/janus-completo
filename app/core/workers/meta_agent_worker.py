"""
Meta-Agent Cycle Worker

Consome mensagens da fila janus.meta_agent.cycle e dispara ciclos de análise
pontuais do Meta-Agente.
"""
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any

from prometheus_client import Counter, Histogram

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import TaskMessage, QueueName

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
            f"\u2713 Meta-Agente ciclo concluído (mode={mode}): status={report.overall_status}, duration={duration:.3f}s"
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
    logger.info("\u2713 Worker do Meta-Agente iniciado.")
    return consumer_task