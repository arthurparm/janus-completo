import logging
import json
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
    code = state.data_payload.script_code
    return await get_formatted_prompt(
        "debate_critic_prompt",
        goal=goal,
        code=code or "",
    )

@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_DEBATE_CRITIC.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_critic_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "debate_critic"
        
        logger.info(f"Debate Critic processing task {state.task_id}")

        llm_service = LLMService(LLMRepository())
        prompt = await _build_prompt(state)
        
        result = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.PRIMARY_ASSISTANT, 
            priority=ModelPriority.HIGH_QUALITY,
        )
        
        response = result.get("response", "")
        
        # Parse JSON
        try:
            # Try to find JSON block
            import re
            match = re.search(r"```json\n(.*?)```", response, re.DOTALL)
            if not match:
                # Try finding just braces
                match = re.search(r"\{.*\}", response, re.DOTALL)
            
            json_str = match.group(1) if match and "json" in match.group(0) else (match.group(0) if match else response)
            
            # Clean up potential markdown if not caught by regex
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            critique = json.loads(json_str)
            
            is_approved = critique.get("approved", False)
            issues = critique.get("issues", [])
            comments = critique.get("general_comments", "")
            
            # Update Payload
            state.data_payload.approved = is_approved
            state.data_payload.review_notes = f"Status: {'Approved' if is_approved else 'Rejected'}\nIssues: {json.dumps(issues, indent=2)}\nComments: {comments}"
            
        except Exception as e:
            logger.error(f"Failed to parse Critic JSON: {e}")
            state.data_payload.approved = False
            state.data_payload.review_notes = f"CRITIC ERROR: Could not parse output. Raw output: {response}"
            
        state.history.append({
            "agent_role": "debate_critic",
            "action": "critique_generated",
            "notes": f"Approved: {state.data_payload.approved}",
            "timestamp": datetime.utcnow().timestamp()
        })
        
        # Next Step Logic
        if state.data_payload.approved:
            # Done!
            logger.info(f"Task {state.task_id} APPROVED by Debate Critic.")
            # We can route to 'router' or just leave it. 
            # If we want to notify completion, we might send to router with status 'completed'
            state.status = "completed"
            state.next_agent_role = "router" # Return to router/meta-agent
        else:
             # Check max iterations
            current_iter = state.data_payload.self_healing_iterations or 0
            state.data_payload.self_healing_iterations = current_iter + 1
            
            if current_iter >= 5: # Max iterations hardcoded
                logger.warning(f"Max debate iterations reached for task {state.task_id}")
                state.status = "max_iterations_reached"
                state.next_agent_role = "router"
                state.data_payload.review_notes += "\n[SYSTEM]: Max iterations reached."
            else:
                state.next_agent_role = "debate_proponent"
        
        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        
    except Exception as e:
        logger.error(f"Debate Critic failed: {e}", exc_info=True)
        raise

async def start_debate_critic_worker():
    logger.info("Starting Debate Critic Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_DEBATE_CRITIC.value,
        callback=process_critic_task,
        prefetch_count=5,
    )
    logger.info("✓ Debate Critic Worker started.")
    return consumer_task
