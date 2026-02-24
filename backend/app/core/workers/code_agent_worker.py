"""
Code Agent Worker

Consome a fila JANUS.tasks.agent.coder, gera código com LLM e decide
próximo agente (Professor ou Sandbox) com base em heurísticas de complexidade.
"""

import logging
from datetime import datetime
from typing import Any

from app.config import settings
from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


async def _build_coding_prompt(
    state: TaskState, compilation_error: str | None = None
) -> str:
    goal = state.original_goal
    review_notes = state.data_payload.review_notes
    context = state.data_payload.context
    thinker_plan = state.data_payload.thinker_plan
    return await get_formatted_prompt(
        "code_agent_task",
        goal=goal,
        thinker_plan=thinker_plan or "",
        context=context or "",
        review_notes=review_notes or "",
        previous_error=compilation_error or "",
    )


def _estimate_complexity(code: str) -> int:
    lines = code.count("\n") + 1
    imports = sum(
        1
        for line in code.splitlines()
        if line.strip().startswith("import") or line.strip().startswith("from ")
    )
    functions = sum(1 for line in code.splitlines() if line.strip().startswith("def "))
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

        # Deep Self-Healing: Retry loop for compiler errors
        max_iterations = settings.CODER_MAX_SELF_HEALING_ITERATIONS if settings.CODER_SELF_HEALING_ENABLED else 1
        code = ""
        compilation_error = None

        for iteration in range(max_iterations):
            # Build prompt (includes previous error if any)
            prompt = await _build_coding_prompt(state, compilation_error if iteration > 0 else "")

            result = await llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.CODE_GENERATOR,
                priority=ModelPriority.HIGH_QUALITY,
                timeout_seconds=None,
            )
            code_response = result.get("response", "")

            # Extract code from markdown block
            import re
            match = re.search(r"```python\n(.*?)```", code_response, re.DOTALL)
            if not match:
                match = re.search(r"```\n(.*?)```", code_response, re.DOTALL)

            if match:
                code = match.group(1)
            else:
                # Fallback: if no markdown block, assume raw code if appropriate (less likely with new prompt)
                code = code_response

            # Try to validate code syntax
            if settings.CODER_SELF_HEALING_ENABLED:
                validation_result = _validate_code_syntax(code)
                if validation_result["valid"]:
                    logger.info(
                        f"Code validated on iteration {iteration + 1}/{max_iterations}",
                        extra={"task_id": state.task_id},
                    )
                    break
                else:
                    compilation_error = validation_result["error"]
                    logger.warning(
                        f"Code validation failed on iteration {iteration + 1}, retrying...",
                        extra={"task_id": state.task_id, "error": compilation_error[:200]},
                    )
            else:
                break  # No self-healing, skip validation loop

        lines_count = code.count("\n") + 1
        state.data_payload.script_code = code
        state.data_payload.self_healing_iterations = iteration + 1
        state.history.append(
            {
                "agent_role": "coder",
                "action": "code_generated",
                "notes": f"lines={lines_count}, iterations={iteration + 1}",
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        # Red Team Intercept: Todo código deve ser auditado antes de revisão ou execução
        state.next_agent_role = "red_team"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        complexity = _estimate_complexity(code)
        logger.info(
            "CodeAgent produziu código e encaminhou",
            extra={
                "task_id": state.task_id,
                "next": state.next_agent_role,
                "complexity": complexity,
                "iterations": iteration + 1,
            },
        )
    except Exception as e:
        logger.error(f"CodeAgent falhou: {e}", exc_info=True)
        raise


def _validate_code_syntax(code: str) -> dict[str, Any]:
    """
    Validate Python code syntax using compile().
    
    Returns:
        Dict with 'valid' bool and 'error' string if invalid.
    """
    try:
        compile(code, "<string>", "exec")
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"SyntaxError: {e.msg} at line {e.lineno}: {e.text}",
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


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
