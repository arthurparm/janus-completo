"""
Async Neural Training Worker

Consumes training tasks from RabbitMQ and triggers LearningRepository training process.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage
from app.repositories.learning_repository import get_learning_repository

logger = structlog.get_logger(__name__)


@protect_against_poison_pills(
    queue_name=QueueName.NEURAL_TRAINING.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_neural_training_task(task: TaskMessage) -> None:
    """Process a neural training task by invoking the LearningRepository."""
    try:
        payload = task.payload or {}
        dataset_version: str | None = payload.get("dataset_version")
        model_name: str | None = payload.get("model_name")
        training_params: dict[str, Any] | None = payload.get("training_params") or {}

        repo = get_learning_repository()
        summary = await repo.run_training_process(
            dataset_version=dataset_version,
            model_name=model_name,
            training_params=training_params,
        )
        logger.info("log_info", message=f"✓ Neural training task completed: task_id={task.task_id}, summary={str(summary)[:200]}"
        )
    except Exception as e:
        logger.error("log_error", message=f"Neural training task failed: task_id={task.task_id}, error={e}",
            exc_info=True,
        )
        raise


async def publish_neural_training_task(
    dataset_version: str | None = None,
    model_name: str | None = None,
    training_params: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> str:
    """Publish a neural training task to the broker."""
    task_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "dataset_version": dataset_version,
        "model_name": model_name,
        "training_params": training_params or {},
    }
    if user_id is not None:
        payload["user_id"] = user_id
    task_message = TaskMessage(
        task_id=task_id,
        task_type="neural_training",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )
    serialized = task_message.model_dump_json()
    broker = await get_broker()
    await broker.publish(queue_name=QueueName.NEURAL_TRAINING.value, message=serialized)
    logger.info("log_info", message=f"Published neural training task: task_id={task_id}, model={model_name}, dataset={dataset_version}"
    )
    return task_id


class NeuralTrainingWorker:
    name = "neural_training"

    def __init__(self, prefetch_count: int = 2):
        self._prefetch_count = prefetch_count
        self._consumer_task = None
        self._running = False

    async def start(self) -> None:
        broker = await get_broker()
        self._consumer_task = broker.start_consumer(
            queue_name=QueueName.NEURAL_TRAINING.value,
            callback=process_neural_training_task,
            prefetch_count=self._prefetch_count,
        )
        self._running = True
        logger.info("NeuralTrainingWorker started")

    async def stop(self) -> None:
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None
        logger.info("NeuralTrainingWorker stopped")

    def is_healthy(self) -> bool:
        return self._running and self._consumer_task is not None and not self._consumer_task.done()

    def get_status(self) -> dict:
        return {"running": self._running}


async def start_neural_training_worker():
    """Start the neural training consumer worker."""
    logger.info("Starting neural training worker...")
    worker = NeuralTrainingWorker()
    await worker.start()
    return worker
