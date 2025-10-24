"""
Professor Agent Worker

Consome a fila JANUS.tasks.agent.professor, revisa código com LLM e decide
se retorna ao CodeAgent para correções ou segue para Sandbox.
"""
import logging
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import TaskMessage, TaskState, QueueName
from app.services.collaboration_service import CollaborationService
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.llm_service import LLMService
from app.repositories.llm_repository import LLMRepository
from app.core.llm import ModelRole, ModelPriority

logger = logging.getLogger(__name__)


def _build_review_prompt(state: TaskState) -> str:
    code = state.data_payload.get("script_code", "")
    prompt = [
        "Revise o código a seguir com foco em correção, clareza e segurança.",
        "Se houver problemas, explique sucintamente e sugira correções objetivas.",
        "Se estiver correto, reconheça e recomende testes mínimos.",
        "Código:",
        code,
    ]
    return "\n".join(prompt)


def _has_errors(review: str) -> bool:
    text = review.lower()
    hints = ["erro", "bug", "corrig", "falha", "inseguro", "exceção"]
    return any(h in text for h in hints)


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_PROFESSOR.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_professor_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "professor"

        code = state.data_payload.get("script_code")
        if not code:
            # Sem código para revisar, encaminhar ao coder
            state.next_agent_role = "coder"
            service = CollaborationService(CollaborationRepository())
            await service.pass_task(state)
            return

        llm_service = LLMService(LLMRepository())
        prompt = _build_review_prompt(state)
        result = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.KNOWLEDGE_CURATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=None,
        )
        review = result.get("response", "")
        state.data_payload["review_notes"] = review
        state.history.append({
            "agent_role": "professor",
            "action": "code_reviewed",
            "notes": f"errors={'yes' if _has_errors(review) else 'no'}",
            "timestamp": datetime.utcnow().timestamp(),
        })

        if _has_errors(review):
            state.next_agent_role = "coder"
        else:
            state.next_agent_role = "sandbox"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "ProfessorAgent revisou e encaminhou",
            extra={"task_id": state.task_id, "next": state.next_agent_role}
        )
    except Exception as e:
        logger.error(f"ProfessorAgent falhou: {e}", exc_info=True)
        raise


async def start_professor_agent_worker():
    logger.info("Iniciando Professor Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_PROFESSOR.value,
        callback=process_professor_task,
        prefetch_count=5,
    )
    logger.info("✓ Professor Agent Worker iniciado.")
    return consumer_task
