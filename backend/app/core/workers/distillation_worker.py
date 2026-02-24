import structlog
from app.core.infrastructure.message_broker import get_broker
from app.core.knowledge.distillation_service import DistillationService
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState

logger = structlog.get_logger(__name__)

@protect_against_poison_pills(
    queue_name=QueueName.TASKS_KNOWLEDGE_DISTILLATION.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_distillation_task(task: TaskMessage) -> None:
    try:
        logger.info("log_info", message=f"DistillationWorker recebeu tarefa: {task.task_id}")

        raw_state = (task.payload or {}).get("task_state", {})
        if not raw_state:
             logger.warning("Payload vazio ou inválido na tarefa de destilação.")
             return

        state = TaskState(**raw_state)

        # Instantiate service (dataset path could be config-injected)
        service = DistillationService()

        # Process
        saved = service.process_task(state)

        if saved:
            logger.info("log_info", message=f"✓ Tarefa {state.task_id} destilada e salva no dataset.")
        else:
            logger.debug("log_debug", message=f"Tarefa {state.task_id} descartada (não atendeu critérios de qualidade).")

    except Exception as e:
        logger.error("log_error", message=f"Erro no DistillationWorker: {e}", exc_info=True)
        # Não damos raise para evitar retry infinito de tarefa "ruim" (dataset poisoning)
        # Poison pill handler já protege, mas aqui preferimos falhar silenciosamente para não travar fila

async def start_distillation_worker():
    logger.info("Iniciando Distillation Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_KNOWLEDGE_DISTILLATION.value,
        callback=process_distillation_task,
        prefetch_count=5,
    )
    logger.info("✓ Distillation Worker iniciado.")
    return consumer_task
