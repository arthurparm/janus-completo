"""
Thinker Agent Worker (Reasoning Node)

Consome a fila JANUS.tasks.agent.thinker.
Este agente atua antes do CodeAgent, usando modelos de raciocínio (como DeepSeek R1)
para planejar a arquitetura e a lógica antes de qualquer código ser escrito.
"""
import structlog
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = structlog.get_logger(__name__)


async def _build_thinking_prompt(state: TaskState) -> str:
    goal = state.original_goal
    context = state.data_payload.context or ""
    return await get_formatted_prompt(
        "agent_thinker",
        goal=goal,
        context=context,
        agent_scratchpad="",
    )


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_THINKER.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_thinker_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "thinker"

        llm_service = LLMService(LLMRepository())
        prompt = await _build_thinking_prompt(state)

        # Usa um role/priority que mapeie para o modelo de raciocínio (ex: DeepSeek R1)
        # Se não houver role específico 'THINKING', usamos KNOWLEDGE_CURATOR ou ORCHESTRATOR
        # com prioridade máxima, e assumimos que a config do LLM (DeepSeek) está lá.
        result = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR, # Idealmente seria um novo ModelRole.REASONING
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=600, # Raciocínio pode demorar
        )
        plan = result.get("response", "")

        # Armazena o plano no payload para o CodeAgent usar
        state.data_payload.thinker_plan = plan

        state.history.append(
            {
                "agent_role": "thinker",
                "action": "plan_generated",
                "notes": f"plan_length={len(plan)}",
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        # O próximo passo é SEMPRE o CoderAgent para executar o plano
        state.status = "in_progress"
        state.next_agent_role = "coder"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "ThinkerAgent gerou plano e encaminhou para Coder",
            extra={"task_id": state.task_id, "next": state.next_agent_role},
        )
    except Exception as e:
        logger.error("thinker_agent_failed", error=str(e), exc_info=True)
        raise


async def start_thinker_agent_worker():
    logger.info("Iniciando Thinker Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_THINKER.value,
        callback=process_thinker_task,
        prefetch_count=3, # Menor prefetch pois tasks demoram mais
    )
    logger.info("✓ Thinker Agent Worker iniciado.")
    return consumer_task
