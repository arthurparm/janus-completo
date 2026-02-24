"""
Async Agent Tasks Worker

Consumes agent task messages from RabbitMQ and runs the agent asynchronously.
"""

import asyncio
import structlog
import uuid
from datetime import datetime
from typing import Any

import msgpack
from starlette.requests import Request

from app.config import settings
from app.core.agents.agent_manager import AgentManager
from app.core.infrastructure.enums import AgentType
from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.resilience import CircuitBreaker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage

logger = structlog.get_logger(__name__)


# Bulkheads e Circuitos por agente
_agent_bulkheads: dict[AgentType, asyncio.Semaphore] = {}
_agent_circuits: dict[AgentType, CircuitBreaker] = {}


def _get_bulkhead(agent_type: AgentType) -> asyncio.Semaphore:
    limits = getattr(settings, "AGENT_BULKHEAD_LIMITS", {}) or {}
    default_limit = int(getattr(settings, "AGENT_BULKHEAD_DEFAULT_LIMIT", 2) or 2)
    limit = int(limits.get(agent_type.value, default_limit) or default_limit)
    sem = _agent_bulkheads.get(agent_type)
    if sem is None:
        sem = asyncio.Semaphore(limit)
        _agent_bulkheads[agent_type] = sem
    return sem


def _get_circuit(agent_type: AgentType) -> CircuitBreaker:
    default_threshold = int(getattr(settings, "AGENT_CIRCUIT_FAILURE_THRESHOLD", 3) or 3)
    default_recovery = int(getattr(settings, "AGENT_CIRCUIT_RECOVERY_TIMEOUT", 30) or 30)
    cfg_map = getattr(settings, "AGENT_CIRCUIT_CONFIG", {}) or {}
    if isinstance(cfg_map, dict) and agent_type.value in cfg_map:
        th = int(
            cfg_map[agent_type.value].get("failure_threshold", default_threshold)
            or default_threshold
        )
        rt = int(
            cfg_map[agent_type.value].get("recovery_timeout", default_recovery) or default_recovery
        )
    else:
        th = default_threshold
        rt = default_recovery
    cb = _agent_circuits.get(agent_type)
    if cb is None:
        cb = CircuitBreaker(failure_threshold=th, recovery_timeout=rt)
        _agent_circuits[agent_type] = cb
    return cb


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

        # Bulkhead & Circuit por agente
        bulkhead = _get_bulkhead(agent_type)
        circuit = _get_circuit(agent_type)

        await bulkhead.acquire()
        try:
            manager = AgentManager()

            async def _execute():
                return await manager.arun_agent(
                    question=question,
                    agent_type=agent_type,
                    request=dummy_request,
                )

            result = await circuit.call_async(_execute)

            logger.info("log_info", message=f"\u2713 Agent task completed: task_id={task.task_id}, type={agent_type}, result={str(result)[:200]}"
            )
        finally:
            bulkhead.release()
    except Exception as e:
        logger.error("log_error", message=f"Agent task failed: task_id={task.task_id}, error={e}", exc_info=True)
        raise


async def publish_agent_task(question: str, agent_type: AgentType | str) -> str:
    """Publish an agent task message to the broker."""
    task_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "question": question,
        "agent_type": agent_type if isinstance(agent_type, str) else agent_type.value,
    }
    task_message = TaskMessage(
        task_id=task_id,
        task_type="agent_task",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )

    serialized = msgpack.packb(task_message.model_dump(), use_bin_type=True)
    broker = await get_broker()
    await broker.publish(
        queue_name=QueueName.AGENT_TASKS.value, message=serialized, use_msgpack=True
    )

    logger.info("log_info", message=f"Published agent task: task_id={task_id}, type={payload['agent_type']}")
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
    logger.info("\u2713 Agent tasks worker started.")
    return consumer_task
