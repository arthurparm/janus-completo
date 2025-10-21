"""
Router Worker (Rececionista)

Consome a fila central JANUS.tasks.router e decide o próximo agente
para o TaskState usando o Planner na decomposição inicial.
"""
import logging
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.core.autonomy.planner import build_plan_for_goal
from app.services.collaboration_service import CollaborationService
from app.repositories.collaboration_repository import CollaborationRepository
from app.models.schemas import TaskMessage, TaskState, QueueName

logger = logging.getLogger(__name__)


def _infer_first_agent(original_goal: str) -> str:
    """Usa o Planner para sugerir o primeiro agente; fallback para 'coder'."""
    try:
        plan = build_plan_for_goal(original_goal)
        steps = plan.get("steps", []) if isinstance(plan, dict) else []
        # Heurística simples: primeira ação geralmente é escrever código
        return "coder"
    except Exception:
        return "coder"


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_ROUTER.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_router_task(task: TaskMessage) -> None:
    """Processa mensagens de roteamento e encaminha para o próximo agente."""
    try:
        payload = task.payload or {}
        raw_state = payload.get("task_state") or {}
        state = TaskState(**raw_state)

        # Se não há próximo agente definido, inferir o primeiro
        if not state.next_agent_role:
            state.next_agent_role = _infer_first_agent(state.original_goal)
        state.current_agent_role = "router"

        # Registrar no histórico
        state.history.append(
            {
                "agent_role": "router",
                "action": "routed",
                "notes": f"next={state.next_agent_role}",
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info("Router encaminhou TaskState", task_id=state.task_id, next_role=state.next_agent_role)
    except Exception as e:
        logger.error(f"Router falhou ao processar TaskState: {e}", exc_info=True)
        raise


async def start_router_worker():
    """Inicia o consumidor da fila central do Router."""
    logger.info("Iniciando Router Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_ROUTER.value,
        callback=process_router_task,
        prefetch_count=10,
    )
    logger.info("✓ Router Worker iniciado.")
    return consumer_task
