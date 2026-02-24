from __future__ import annotations

import asyncio
from typing import Any

import structlog
from prometheus_client import Counter, Gauge

from app.models.schemas import QueueName
from app.repositories.outbox_repository import OutboxEventRecord, OutboxRepository
from app.core.infrastructure.message_broker import get_broker

logger = structlog.get_logger(__name__)

OUTBOX_DISPATCH_TOTAL = Counter(
    "outbox_dispatch_total",
    "Eventos processados pelo dispatcher de outbox",
    ["status", "event_type"],
)
OUTBOX_PENDING_GAUGE = Gauge(
    "outbox_events_pending_total",
    "Eventos pendentes/retry no outbox",
)
OUTBOX_DEAD_GAUGE = Gauge(
    "outbox_events_dead_total",
    "Eventos mortos no outbox",
)


class OutboxService:
    def __init__(self, repo: OutboxRepository):
        self._repo = repo
        self._task: asyncio.Task | None = None
        self._running = False
        self._interval_seconds = 5

    def enqueue_consolidation(
        self,
        *,
        payload: dict[str, Any],
        aggregate_id: str | None,
        dedupe_key: str | None,
    ) -> int:
        return self._repo.enqueue(
            event_type="knowledge_consolidation",
            payload_json=payload,
            aggregate_id=aggregate_id,
            dedupe_key=dedupe_key,
        )

    async def dispatch_pending(self, *, limit: int = 50) -> dict[str, int]:
        claimed = self._repo.claim_pending(limit=limit)
        if not claimed:
            self._update_gauges()
            return {"claimed": 0, "sent": 0, "retry": 0, "dead": 0}

        sent = 0
        retry = 0
        dead = 0
        for item in claimed:
            ok, status = await self._dispatch_item(item)
            if ok:
                sent += 1
                continue

            if status == "dead":
                dead += 1
            else:
                retry += 1

        self._update_gauges()
        return {"claimed": len(claimed), "sent": sent, "retry": retry, "dead": dead}

    async def _dispatch_item(self, item: OutboxEventRecord) -> tuple[bool, str]:
        try:
            queue_name = self._resolve_queue(item.event_type)
            broker = await get_broker()
            await broker.publish(queue_name=queue_name, message=item.payload_json)
            self._repo.mark_sent(item.id)
            OUTBOX_DISPATCH_TOTAL.labels(status="sent", event_type=item.event_type).inc()
            return True, "sent"
        except Exception as e:
            next_status = self._repo.mark_retry(item.id, error=str(e))
            metric_status = "dead" if next_status == "dead" else "retry"
            OUTBOX_DISPATCH_TOTAL.labels(status=metric_status, event_type=item.event_type).inc()
            logger.warning(
                "outbox_dispatch_failed",
                event_id=item.id,
                event_type=item.event_type,
                error=str(e),
            )
            return False, metric_status

    async def start(self, *, interval_seconds: int = 5) -> None:
        if self._running:
            return
        self._interval_seconds = max(1, int(interval_seconds))
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Outbox dispatcher started", interval_seconds=self._interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Outbox dispatcher stopped")

    async def reconcile(self, *, limit: int = 100, requeue_dead: bool = True) -> dict[str, Any]:
        requeued = 0
        if requeue_dead:
            requeued = self._repo.requeue_dead(limit=limit)
        dispatched = await self.dispatch_pending(limit=limit)
        stats = self._repo.get_stats()
        self._update_gauges(stats=stats)
        return {"requeued_dead": requeued, "dispatch": dispatched, "stats": stats}

    def get_stats(self) -> dict[str, int]:
        stats = self._repo.get_stats()
        self._update_gauges(stats=stats)
        return stats

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self.dispatch_pending(limit=50)
            except Exception as e:
                logger.warning("outbox_dispatch_loop_error", error=str(e))
            await asyncio.sleep(self._interval_seconds)

    def _resolve_queue(self, event_type: str) -> str:
        if event_type == "knowledge_consolidation":
            return str(QueueName.KNOWLEDGE_CONSOLIDATION.value)
        raise ValueError(f"Unsupported outbox event type: {event_type}")

    def _update_gauges(self, *, stats: dict[str, int] | None = None) -> None:
        data = stats or self._repo.get_stats()
        pending_total = int(data.get("pending", 0)) + int(data.get("retry", 0))
        dead_total = int(data.get("dead", 0))
        OUTBOX_PENDING_GAUGE.set(pending_total)
        OUTBOX_DEAD_GAUGE.set(dead_total)
