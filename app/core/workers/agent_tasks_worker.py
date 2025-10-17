"""
Async Agent Tasks Worker

Consumes agent task messages from RabbitMQ and runs the agent asynchronously.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from starlette.requests import Request

from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.enums import AgentType
from app.core.agents.agent_manager import AgentManager
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import TaskMessage, QueueName

logger = logging.getLogger(__name__)


def _parse_agent_type(value: Any) -> AgentType:
    try:
        if isinstance(value, AgentType):
            return value
        if isinstance(value, str):
            return AgentType(value)
        raise ValueError(f"Unsupported agent_type: {value}")
    except Exception as e:
        raise ValueError(f"Invalid agent_type '{value}': {e}")


@protect_against_poison_pills(
    queue_name=QueueName.AGENT_TASKS.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_agent_task(task: TaskMessage) -> None:
    """Process an agent task message and run the agent."""
    try:
        payload = task.payload or {}
        question = payload.get("question")
        agent_type_raw = payload.get("agent_type")
        if not question or not agent_type_raw:
            raise ValueError("'question' and 'agent_type' are required in payload")

        agent_type = _parse_agent_type(agent_type_raw)

        # Construct a minimal Starlette Request for compatibility
        scope = {"type": "http", "method": "POST", "path": "/agent/run"}
        dummy_request = Request(scope)

        manager = AgentManager()
        result = await manager.arun_agent(
            question=question,
            agent_type=agent_type,
            request=dummy_request,
        )

        logger.info(
            f"✓ Agent task completed: task_id={task.task_id}, type={agent_type}, result={str(result)[:200]}"
        )
    except Exception as e:
        logger.error(f"Agent task failed: task_id={task.task_id}, error={e}", exc_info=True)
        raise


async def publish_agent_task(question: str, agent_type: AgentType | str) -> str:
    """Publish an agent task message to the broker."""
    task_id = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "question": question,
        "agent_type": agent_type if isinstance(agent_type, str) else agent_type.value,
    }
    task_message = TaskMessage(
        task_id=task_id,
        task_type="agent_task",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )

    serialized = task_message.model_dump_json()
    broker = await get_broker()
    await broker.publish(queue_name=QueueName.AGENT_TASKS.value, message=serialized)

    logger.info(f"Published agent task: task_id={task_id}, type={payload['agent_type']}")
    return task_id


async def start_agent_tasks_worker():
    """Start the agent tasks consumer worker."""
    logger.info("Starting agent tasks worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.AGENT_TASKS.value,
        callback=process_agent_task,
        prefetch_count=10,
    )
    logger.info("✓ Agent tasks worker started.")
    return consumer_task