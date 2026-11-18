from unittest.mock import AsyncMock

import pytest

from app.core.monitoring.health_monitor import HealthMonitor, HealthStatus
from app.core.workers.life_cycle_worker import LifeCycleWorker


class _Clock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.mark.asyncio
async def test_pulse_publishes_real_maintenance_and_reports_health() -> None:
    memory = AsyncMock()
    memory.recall_recent_failures.return_value = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    publisher = AsyncMock()
    clock = _Clock()
    worker = LifeCycleWorker(
        memory_service=memory,
        clock=clock,
        consolidation_publisher=publisher,
    )
    worker._running = True

    await worker._pulse()

    publisher.assert_awaited_once_with(
        payload={"mode": "batch", "limit": 50, "min_score": 0.0}
    )
    memory.recall_recent_failures.assert_awaited_once_with(
        limit=5, timeframe_seconds=600
    )
    health = worker.get_health_status()
    assert health["status"] == "healthy"
    assert health["details"]["pulse_count"] == 1
    assert health["details"]["consolidation_publish_count"] == 1
    assert health["details"]["recent_failures_observed"] == 3


@pytest.mark.asyncio
async def test_failed_publication_is_observable_and_retried_on_next_pulse() -> None:
    memory = AsyncMock()
    memory.recall_recent_failures.return_value = []
    publisher = AsyncMock(side_effect=[RuntimeError("broker down"), None])
    clock = _Clock()
    worker = LifeCycleWorker(
        memory_service=memory,
        clock=clock,
        consolidation_publisher=publisher,
    )
    worker._running = True

    await worker._pulse()

    degraded = worker.get_health_status()
    assert degraded["status"] == "degraded"
    assert degraded["details"]["last_error"] == "consolidation:RuntimeError"
    assert degraded["details"]["last_consolidation_at"] is None

    clock.now += 30
    await worker._pulse()

    assert publisher.await_count == 2
    recovered = worker.get_health_status()
    assert recovered["status"] == "healthy"
    assert recovered["details"]["consecutive_failed_pulses"] == 0
    assert recovered["details"]["consolidation_publish_count"] == 1


@pytest.mark.asyncio
async def test_start_and_stop_are_idempotent_and_report_stopped_health() -> None:
    memory = AsyncMock()
    memory.recall_recent_failures.return_value = []
    worker = LifeCycleWorker(
        memory_service=memory,
        interval_seconds=60,
        consolidation_publisher=AsyncMock(),
    )

    await worker.start()
    first_task = worker._task
    await worker.start()
    assert worker._task is first_task
    assert worker.get_health_status()["status"] == "healthy"

    await worker.stop()
    await worker.stop()
    assert worker.get_health_status()["status"] == "unhealthy"


def test_constructor_rejects_invalid_intervals() -> None:
    with pytest.raises(ValueError, match="interval_seconds"):
        LifeCycleWorker(memory_service=AsyncMock(), interval_seconds=0)

    with pytest.raises(ValueError, match="consolidation_interval_seconds"):
        LifeCycleWorker(
            memory_service=AsyncMock(), consolidation_interval_seconds=0
        )


@pytest.mark.asyncio
async def test_health_contract_is_consumed_by_kernel_monitor() -> None:
    worker = LifeCycleWorker(
        memory_service=AsyncMock(), consolidation_publisher=AsyncMock()
    )
    worker._running = True
    monitor = HealthMonitor()
    monitor.register_health_check(
        "life_cycle_worker", worker.get_health_status, is_critical=True
    )

    result = await monitor.check_component("life_cycle_worker")

    assert result.status is HealthStatus.HEALTHY
    assert result.details["running"] is True
