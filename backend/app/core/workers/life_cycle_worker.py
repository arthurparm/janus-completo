import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import structlog

from app.core.workers.async_consolidation_worker import publish_consolidation_task

logger = structlog.get_logger(__name__)


class FailureMemory(Protocol):
    async def recall_recent_failures(
        self, *, limit: int, timeframe_seconds: int
    ) -> list[Any]: ...


ConsolidationPublisher = Callable[..., Awaitable[Any]]


class LifeCycleWorker:
    """Executa manutenção periódica sem autorizar ou executar metas."""

    def __init__(
        self,
        *,
        memory_service: FailureMemory,
        interval_seconds: float = 30,
        consolidation_interval_seconds: float = 600,
        clock: Callable[[], float] = time.time,
        consolidation_publisher: ConsolidationPublisher = publish_consolidation_task,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        if consolidation_interval_seconds <= 0:
            raise ValueError("consolidation_interval_seconds must be greater than zero")

        self._memory_service = memory_service
        self._interval = float(interval_seconds)
        self._consolidation_interval = float(consolidation_interval_seconds)
        self._clock = clock
        self._consolidation_publisher = consolidation_publisher
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._last_consolidation_ts: float | None = None
        self._last_pulse_ts: float | None = None
        self._last_error_ts: float | None = None
        self._last_error: str | None = None
        self._pulse_count = 0
        self._consolidation_publish_count = 0
        self._recent_failures_observed = 0
        self._consecutive_failed_pulses = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="janus-life-cycle-worker")
        logger.info("life_cycle_worker_started", interval_seconds=self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("life_cycle_worker_stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._pulse()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._record_pulse_failure(("pulse", exc))
                logger.exception("life_cycle_pulse_unexpected_failure")

            await asyncio.sleep(self._interval)

    async def _pulse(self) -> None:
        """Executa uma rodada independente de consolidação e diagnóstico."""
        now = self._clock()
        errors: list[tuple[str, Exception]] = []

        if self._consolidation_is_due(now):
            try:
                await self._consolidation_publisher(
                    payload={"mode": "batch", "limit": 50, "min_score": 0.0}
                )
                self._last_consolidation_ts = now
                self._consolidation_publish_count += 1
                logger.info("life_cycle_consolidation_published")
            except Exception as exc:
                errors.append(("consolidation", exc))
                logger.exception("life_cycle_consolidation_publish_failed")

        try:
            failures = await self._memory_service.recall_recent_failures(
                limit=5, timeframe_seconds=600
            )
            self._recent_failures_observed = len(failures)
            if self._recent_failures_observed >= 3:
                logger.warning(
                    "life_cycle_recent_failures_detected",
                    failure_count=self._recent_failures_observed,
                    timeframe_seconds=600,
                )
        except Exception as exc:
            errors.append(("failure_memory", exc))
            logger.exception("life_cycle_failure_scan_failed")

        self._pulse_count += 1
        self._last_pulse_ts = now
        if errors:
            self._record_pulse_failure(*errors)
        else:
            self._consecutive_failed_pulses = 0
            self._last_error = None

    def _consolidation_is_due(self, now: float) -> bool:
        return (
            self._last_consolidation_ts is None
            or now - self._last_consolidation_ts >= self._consolidation_interval
        )

    def _record_pulse_failure(self, *errors: tuple[str, Exception]) -> None:
        self._consecutive_failed_pulses += 1
        self._last_error_ts = self._clock()
        self._last_error = ", ".join(
            f"{component}:{type(exc).__name__}" for component, exc in errors
        )

    def get_health_status(self) -> dict[str, Any]:
        if not self._running:
            status = "unhealthy"
            message = "Life-cycle maintenance worker is stopped"
        elif self._consecutive_failed_pulses:
            status = "degraded"
            message = "Life-cycle maintenance completed with failures"
        else:
            status = "healthy"
            message = "Life-cycle maintenance worker is running"

        return {
            "status": status,
            "message": message,
            "details": {
                "running": self._running,
                "pulse_count": self._pulse_count,
                "last_pulse_at": self._last_pulse_ts,
                "consolidation_publish_count": self._consolidation_publish_count,
                "last_consolidation_at": self._last_consolidation_ts,
                "recent_failures_observed": self._recent_failures_observed,
                "consecutive_failed_pulses": self._consecutive_failed_pulses,
                "last_error": self._last_error,
                "last_error_at": self._last_error_ts,
            },
        }
