"""
Meta-Agent Cycle Worker

Consumes messages from janus.meta_agent.cycle and triggers async Meta-Agent cycles.
"""

import asyncio
import inspect
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from app.config import settings
from app.core.infrastructure.message_broker import get_broker
from app.core.memory.memory_core import get_memory_db
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage
from app.repositories.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# Worker metrics
_META_AGENT_MESSAGES_TOTAL = Counter(
    "meta_agent_messages_total",
    "Total messages processed by Meta-Agent worker",
    ["outcome", "mode"],
)
_META_AGENT_PROCESSING_SECONDS = Histogram(
    "meta_agent_processing_seconds",
    "Meta-Agent worker cycle processing time",
    ["mode"],
)
_META_AGENT_TRIGGERS_TOTAL = Counter(
    "meta_agent_triggers_total",
    "Total trigger requests received by Meta-Agent worker",
    ["outcome", "mode", "reason"],
)
_META_AGENT_TRIGGER_PRIORITY = Histogram(
    "meta_agent_trigger_priority",
    "Effective trigger priority for Meta-Agent cycles",
    ["mode"],
)
_META_AGENT_TRIGGER_COOLDOWN_REMAINING = Gauge(
    "meta_agent_trigger_cooldown_remaining_seconds",
    "Remaining cooldown before accepting new trigger by mode",
    ["mode"],
)

_memory_service: MemoryService | None = None
_trigger_lock = asyncio.Lock()
_last_trigger_ts_by_mode: dict[str, float] = {}
_last_failure_fingerprint_ts: dict[str, float] = {}


def _clamp_priority(value: int) -> int:
    return max(0, min(9, int(value)))


def _compute_trigger_priority(mode: str, payload: dict[str, Any]) -> int:
    mode = (mode or "single").strip().lower()
    if mode.startswith("scheduled"):
        return _clamp_priority(getattr(settings, "META_AGENT_SCHEDULED_PRIORITY", 2))

    if mode == "failure_event":
        base = int(getattr(settings, "META_AGENT_FAILURE_BASE_PRIORITY", 6))
        score = float(payload.get("score", 0.0) or 0.0)
        score_boost = min(2, max(0, int(round(score * 2))))
        text = f"{payload.get('reason', '')} {payload.get('origin', '')}".lower()
        critical_markers = ("critical", "fatal", "panic", "timeout", "security", "outage")
        marker_boost = 2 if any(m in text for m in critical_markers) else 0
        return _clamp_priority(base + score_boost + marker_boost)

    return 5


def _mode_cooldown_seconds(mode: str) -> int:
    base = int(getattr(settings, "META_AGENT_TRIGGER_COOLDOWN_SECONDS", 20))
    mode = (mode or "single").strip().lower()
    if mode.startswith("scheduled"):
        return max(base, 120)
    if mode == "failure_event":
        return max(base, 10)
    return max(base, 5)


async def _ensure_memory_initialized() -> None:
    global _memory_service
    if _memory_service is None:
        db = await get_memory_db()
        mem_repo = MemoryRepository(db)
        _memory_service = MemoryService(mem_repo)


async def request_meta_agent_cycle(
    mode: str = "single",
    payload: dict[str, Any] | None = None,
    priority: int | None = None,
    force: bool = False,
) -> str | None:
    """
    Queue a Meta-Agent cycle with debounce/cooldown/priority control.
    Returns task_id when queued, or None when dropped.
    """
    now = time.time()
    mode_key = (mode or "single").strip().lower()
    payload = dict(payload or {})

    if mode_key == "failure_event" and not force:
        reason = str(payload.get("reason", "unknown")).strip().lower()
        origin = str(payload.get("origin", "unknown")).strip().lower()
        fingerprint = f"{origin}:{reason}"
        if fingerprint:
            debounce_seconds = int(getattr(settings, "META_AGENT_FAILURE_DEBOUNCE_SECONDS", 30))
            last_fp_ts = _last_failure_fingerprint_ts.get(fingerprint, 0.0)
            elapsed = now - last_fp_ts
            if elapsed < debounce_seconds:
                _META_AGENT_TRIGGERS_TOTAL.labels("dropped", mode_key, "debounce").inc()
                return None
            _last_failure_fingerprint_ts[fingerprint] = now
            if len(_last_failure_fingerprint_ts) > 512:
                cutoff = now - (debounce_seconds * 2)
                for key, ts in list(_last_failure_fingerprint_ts.items()):
                    if ts < cutoff:
                        _last_failure_fingerprint_ts.pop(key, None)

    cooldown = _mode_cooldown_seconds(mode_key)
    async with _trigger_lock:
        last_ts = _last_trigger_ts_by_mode.get(mode_key, 0.0)
        elapsed = now - last_ts
        if not force and elapsed < cooldown:
            _META_AGENT_TRIGGER_COOLDOWN_REMAINING.labels(mode_key).set(max(0.0, cooldown - elapsed))
            _META_AGENT_TRIGGERS_TOTAL.labels("dropped", mode_key, "cooldown").inc()
            return None
        _last_trigger_ts_by_mode[mode_key] = now
        _META_AGENT_TRIGGER_COOLDOWN_REMAINING.labels(mode_key).set(0.0)

    effective_priority = _clamp_priority(
        priority if priority is not None else _compute_trigger_priority(mode_key, payload)
    )
    _META_AGENT_TRIGGER_PRIORITY.labels(mode_key).observe(effective_priority)
    task_id = await publish_meta_agent_cycle(
        mode=mode_key,
        priority=effective_priority,
        payload_extra=payload,
    )
    _META_AGENT_TRIGGERS_TOTAL.labels("queued", mode_key, "ok").inc()
    return task_id


@protect_against_poison_pills(
    queue_name=QueueName.META_AGENT_CYCLE.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_meta_agent_cycle(task: TaskMessage) -> None:
    """Process a single Meta-Agent cycle task."""
    payload = task.payload or {}
    mode = str(payload.get("mode", "single"))
    trigger_priority = payload.get("meta_priority")
    trigger_source = payload.get("source")
    logger.info(
        "Starting meta-agent cycle: task_id=%s, type=%s, mode=%s, source=%s, priority=%s",
        task.task_id,
        task.task_type,
        mode,
        trigger_source,
        trigger_priority,
    )
    start = time.perf_counter()
    try:
        from app.core.agents.meta_agent import get_meta_agent

        meta_agent = get_meta_agent()
        report = await meta_agent.run_analysis_cycle(
            trigger={"mode": mode, "source": trigger_source, "priority": trigger_priority}
        )

        duration = time.perf_counter() - start
        _META_AGENT_PROCESSING_SECONDS.labels(mode).observe(duration)
        _META_AGENT_MESSAGES_TOTAL.labels("success", mode).inc()
        logger.info(
            "Meta-Agent cycle completed: mode=%s status=%s duration=%.3fs",
            mode,
            report.overall_status,
            duration,
        )
    except Exception as e:
        _META_AGENT_MESSAGES_TOTAL.labels("error", mode).inc()
        logger.error("Meta-Agent cycle error task_id=%s: %s", task.task_id, e, exc_info=True)
        raise


async def publish_meta_agent_cycle(
    mode: str = "single",
    priority: int = 5,
    payload_extra: dict[str, Any] | None = None,
) -> str:
    """Publish a cycle request to janus.meta_agent.cycle queue."""
    task_id = str(uuid.uuid4())
    effective_priority = _clamp_priority(priority)

    payload: dict[str, Any] = {"mode": mode, "meta_priority": effective_priority}
    if payload_extra:
        payload.update(payload_extra)

    task_message = TaskMessage(
        task_id=task_id,
        task_type="meta_agent_cycle",
        payload=payload,
        timestamp=datetime.utcnow().timestamp(),
    )

    serialized = task_message.model_dump_json()
    broker = await get_broker()
    await broker.publish(
        queue_name=QueueName.META_AGENT_CYCLE.value,
        message=serialized,
        priority=effective_priority,
    )

    logger.info(
        "Meta-Agent cycle queued: task_id=%s mode=%s priority=%s",
        task_id,
        mode,
        effective_priority,
    )
    return task_id


async def start_meta_agent_worker():
    """Start janus.meta_agent.cycle consumer."""
    logger.info("Starting Meta-Agent worker (cycle queue)...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.META_AGENT_CYCLE.value,
        callback=process_meta_agent_cycle,
        prefetch_count=2,
    )
    logger.info("Meta-Agent worker started.")
    return consumer_task


@protect_against_poison_pills(
    queue_name=QueueName.FAILURE_DETECTED.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_failure_event(task: TaskMessage) -> None:
    """
    Consume janus.failure.detected events and trigger Meta-Agent analysis.
    Also stores a compact memory entry for future diagnostics.
    """
    init_result = _ensure_memory_initialized()
    if inspect.isawaitable(init_result):
        await init_result

    mode = "failure_event"
    start = time.perf_counter()
    try:
        payload = task.payload or {}
        reason = str(payload.get("reason", "unknown"))
        score = float(payload.get("score", 0.0) or 0.0)
        origin = str(payload.get("origin", "unknown"))
        context = payload.get("context", {}) or {}
        ts_iso = str(payload.get("timestamp", datetime.utcnow().isoformat()))

        assert _memory_service is not None
        meta = {
            "status": "failure",
            "error_type": reason,
            "component": origin,
            "score": score,
            "timestamp": ts_iso,
            "queue": QueueName.FAILURE_DETECTED.value,
            "task_id": task.task_id,
        }
        if isinstance(context, dict):
            meta.update(
                {
                    "conversation_id": context.get("conversation_id"),
                    "interaction_id": context.get("interaction_id"),
                    "task_preview": (context.get("task") or "")[:300],
                }
            )
        await _memory_service.add_experience(
            type="action_failure",
            content=f"Failure detected: {reason}",
            metadata=meta,
        )

        queued_task_id = await request_meta_agent_cycle(
            mode=mode,
            payload={
                "source": origin,
                "reason": reason,
                "score": score,
                "timestamp": ts_iso,
            },
        )
        if queued_task_id is None:
            logger.info(
                "Failure event absorbed by debounce/cooldown: origin=%s reason=%s",
                origin,
                reason,
            )

        duration = time.perf_counter() - start
        _META_AGENT_PROCESSING_SECONDS.labels(mode).observe(duration)
        _META_AGENT_MESSAGES_TOTAL.labels("success", mode).inc()
        logger.info(
            "Failure event processed by Meta-Agent: origin=%s reason=%s score=%.2f",
            origin,
            reason,
            score,
        )
    except Exception as e:
        _META_AGENT_MESSAGES_TOTAL.labels("error", mode).inc()
        logger.error("Error processing failure event: %s", e, exc_info=True)
        raise


async def start_failure_event_consumer():
    """Start janus.failure.detected consumer."""
    logger.info("Starting Meta-Agent failure consumer (janus.failure.detected)...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.FAILURE_DETECTED.value,
        callback=process_failure_event,
        prefetch_count=5,
    )
    logger.info("Meta-Agent failure consumer started.")
    return consumer_task
