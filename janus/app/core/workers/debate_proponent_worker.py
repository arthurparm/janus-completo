import logging
from datetime import datetime
from typing import Any

from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

async def _build_prompt(state: TaskState) -> str:
    goal = state.original_goal
    # Review notes from Critic come from payload
    review_notes = state.data_payload.review_notes
    current_code = state.data_payload.script_code
    return await get_formatted_prompt(
        "debate_proponent_prompt",
        goal=goal,
        current_code=current_code or "",
        review_notes=review_notes or "",
    )

@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_DEBATE_PROPONENT.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_proponent_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "debate_proponent"
        
        logger.info(f"Debate Proponent processing task {state.task_id}")

        llm_service = LLMService(LLMRepository())
        prompt = await _build_prompt(state)
        
        result = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.CODE_GENERATOR,
            priority=ModelPriority.HIGH_QUALITY,
        )
        
        response = result.get("response", "")
        
        # Extract code logic
        import re
        match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        if not match:
             match = re.search(r"```\n(.*?)```", response, re.DOTALL)
        
        code = match.group(1) if match else response
        
        # Update State
        state.data_payload.script_code = code
        state.history.append({
            "agent_role": "debate_proponent",
            "action": "proposal_generated",
            "notes": "Code generated/refined",
            "timestamp": datetime.utcnow().timestamp()
        })
        
        # Route to Critic
        state.next_agent_role = "debate_critic"
        
        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(f"Proponent task {state.task_id} passed to Critic")
        
    except Exception as e:
        logger.error(f"Debate Proponent failed: {e}", exc_info=True)
        raise

async def start_debate_proponent_worker():
    logger.info("Starting Debate Proponent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_DEBATE_PROPONENT.value,
        callback=process_proponent_task,
        prefetch_count=5,
    )
    logger.info("✓ Debate Proponent Worker started.")
    return consumer_task
