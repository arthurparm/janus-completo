from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import structlog

try:
    import msgpack
except Exception:
    class _MsgPackCompat:
        @staticmethod
        def packb(obj: Any, use_bin_type: bool = True) -> bytes:
            del use_bin_type
            return json.dumps(obj, ensure_ascii=False).encode("utf-8")

        @staticmethod
        def unpackb(data: bytes | bytearray, raw: bool = False):
            del raw
            if isinstance(data, (bytes, bytearray)):
                return json.loads(data.decode("utf-8"))
            return json.loads(str(data))

    msgpack = _MsgPackCompat()  # type: ignore[assignment]

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage

logger = structlog.get_logger(__name__)


@protect_against_poison_pills(
    queue_name=QueueName.DOCUMENT_INGESTION.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_document_ingestion_task(task: TaskMessage) -> None:
    logger.info(
        "document_ingestion_task_started",
        task_id=task.task_id,
        task_type=task.task_type,
    )
    payload = task.payload or {}
    doc_id = str(payload.get("doc_id") or "").strip()
    if not doc_id:
        raise ValueError("doc_id obrigatório para document_ingestion")

    from app.core.kernel import Kernel

    kernel = Kernel.get_instance()
    service = getattr(kernel, "document_service", None)
    if service is None:
        raise RuntimeError("Document service indisponível no kernel")

    result = await service.process_staged_document(doc_id=doc_id)

    if bool(payload.get("auto_consolidate")) and result.get("status") == "indexed":
        knowledge_service = getattr(kernel, "knowledge_service", None)
        manifest_repo = getattr(kernel, "document_manifest_repo", None)
        manifest = manifest_repo.get_manifest(doc_id) if manifest_repo is not None else None
        if knowledge_service is not None and manifest is not None:
            try:
                await knowledge_service.consolidate_document(
                    user_id=str(manifest.get("user_id")),
                    doc_id=doc_id,
                    limit=50,
                )
            except Exception as exc:
                logger.warning(
                    "document_auto_consolidation_failed",
                    doc_id=doc_id,
                    error=str(exc),
                )

    logger.info(
        "document_ingestion_task_finished",
        task_id=task.task_id,
        doc_id=doc_id,
        status=result.get("status"),
    )


async def publish_document_ingestion_task(payload: dict[str, Any]) -> dict[str, Any]:
    broker = await get_broker()
    task_message = TaskMessage(
        task_id=str(uuid.uuid4()),
        task_type="document_ingestion",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )
    serialized = msgpack.packb(task_message.model_dump(), use_bin_type=True)
    await broker.publish(
        queue_name=QueueName.DOCUMENT_INGESTION.value,
        message=serialized,
        use_msgpack=True,
    )
    return {"status": "ok", "task_id": task_message.task_id}


async def start_document_ingestion_worker():
    logger.info("Starting document ingestion worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.DOCUMENT_INGESTION.value,
        callback=process_document_ingestion_task,
        prefetch_count=1,
    )
    logger.info("Document ingestion worker started.")
    return consumer_task
