"""
Code Agent Worker

Consome a fila JANUS.tasks.agent.coder, gera código com LLM e decide
próximo agente (Professor ou Sandbox) com base em heurísticas de complexidade.
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


def _build_coding_prompt(state: TaskState) -> str:
    goal = state.original_goal
    review_notes = state.data_payload.get("review_notes")
    context = state.data_payload.get("context")
    prompt = [
        f"Objetivo: {goal}",
        "Escreva um script claro, com comentários essenciais e estrutura modular.",
        "Retorne apenas o código final, sem explicações externas.",
    ]
    if context:
        prompt.append(f"Contexto: {context}")
    if review_notes:
        prompt.append(f"Correções solicitadas: {review_notes}")
    return "\n".join(prompt)


def _estimate_complexity(code: str) -> int:
    lines = code.count("\n") + 1
    imports = sum(1 for l in code.splitlines() if l.strip().startswith("import") or l.strip().startswith("from "))
    functions = sum(1 for l in code.splitlines() if l.strip().startswith("def "))
    score = min(10, (lines // 80) + imports + (functions // 3))
    return score


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_CODER.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_code_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "coder"

        llm_service = LLMService(LLMRepository())
        prompt = _build_coding_prompt(state)
        result = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.CODE_GENERATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=None,
        )
        code = result.get("response", "")
        lines_count = code.count("\n") + 1
        state.data_payload["script_code"] = code
        state.history.append({
            "agent_role": "coder",
            "action": "code_generated",
            "notes": f"lines={lines_count}",
            "timestamp": datetime.utcnow().timestamp(),
        })

        complexity = _estimate_complexity(code)
        if complexity > 7:
            state.next_agent_role = "professor"
        else:
            state.next_agent_role = "sandbox"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "CodeAgent produziu código e encaminhou",
            extra={"task_id": state.task_id, "next": state.next_agent_role, "complexity": complexity}
        )
    except Exception as e:
        logger.error(f"CodeAgent falhou: {e}", exc_info=True)
        raise


async def start_code_agent_worker():
    logger.info("Iniciando Code Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_CODER.value,
        callback=process_code_task,
        prefetch_count=5,
    )
    logger.info("✓ Code Agent Worker iniciado.")
    return consumer_task
