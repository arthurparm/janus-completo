import asyncio
from datetime import datetime

import pytest
from app.core import kernel_health
from app.core.monitoring.health_monitor import (
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
)


def _result(component: str, status: HealthStatus) -> HealthCheckResult:
    return HealthCheckResult(
        component=component,
        status=status,
        message=f"{component} is {status.value}",
        details={},
        checked_at=datetime.now(),
        duration_seconds=0.0,
    )


def test_critical_degraded_component_prevents_global_healthy_status():
    monitor = HealthMonitor()
    monitor.register_health_check("postgres", lambda: {"status": "healthy"}, is_critical=True)
    monitor.register_health_check("redis", lambda: {"status": "healthy"}, is_critical=False)
    monitor.register_health_check("worker", lambda: {"status": "healthy"}, is_critical=False)
    monitor.last_results = {
        "postgres": _result("postgres", HealthStatus.DEGRADED),
        "redis": _result("redis", HealthStatus.HEALTHY),
        "worker": _result("worker", HealthStatus.HEALTHY),
    }

    health = monitor.get_system_health()

    assert health["score"] == 83
    assert health["status"] == "degraded"


def test_missing_critical_component_result_prevents_global_healthy_status():
    monitor = HealthMonitor()
    monitor.register_health_check("postgres", lambda: {"status": "healthy"}, is_critical=True)
    monitor.register_health_check("worker", lambda: {"status": "healthy"}, is_critical=False)
    monitor.last_results = {
        "worker": _result("worker", HealthStatus.HEALTHY),
    }

    health = monitor.get_system_health()

    assert health["score"] == 50
    assert health["status"] == "degraded"
    assert health["components"]["postgres"]["status"] == "unknown"
    assert health["components"]["worker"]["status"] == "healthy"


def test_registered_critical_checks_without_any_result_are_reported_as_unknown():
    monitor = HealthMonitor()
    monitor.register_health_check("postgres", lambda: {"status": "healthy"}, is_critical=True)
    monitor.register_health_check("redis", lambda: {"status": "healthy"}, is_critical=False)

    health = monitor.get_system_health()

    assert health["score"] == 0
    assert health["status"] == "degraded"
    assert health["components"]["postgres"]["status"] == "unknown"
    assert health["components"]["redis"]["status"] == "unknown"


@pytest.mark.asyncio
async def test_health_monitor_accepts_canonical_ok_status():
    monitor = HealthMonitor()
    monitor.register_health_check(
        "system_health_api",
        lambda: {"status": "ok", "message": "canonical status"},
        is_critical=True,
    )

    result = await monitor.check_component("system_health_api")

    assert result.status == HealthStatus.HEALTHY
    assert result.message == "canonical status"
    assert result.error is None


@pytest.mark.asyncio
async def test_health_monitor_maps_canonical_error_status_to_unhealthy():
    monitor = HealthMonitor()
    monitor.register_health_check(
        "system_health_api",
        lambda: {"status": "error", "message": "canonical failure"},
        is_critical=True,
    )

    result = await monitor.check_component("system_health_api")

    assert result.status == HealthStatus.UNHEALTHY
    assert result.message == "canonical failure"


@pytest.mark.asyncio
async def test_health_monitor_start_monitoring_is_idempotent():
    monitor = HealthMonitor()

    try:
        await monitor.start_monitoring(interval_seconds=60)
        first_task = monitor._monitoring_task
        await monitor.start_monitoring(interval_seconds=60)
        second_task = monitor._monitoring_task

        assert first_task is second_task
        assert first_task is not None
        assert not first_task.done()
    finally:
        task = monitor._monitoring_task
        monitor.stop_monitoring()
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_neo4j_connection_failure_is_unhealthy(monkeypatch):
    async def fail_get_graph_db():
        raise RuntimeError("neo4j unavailable")

    monkeypatch.setattr(kernel_health, "get_graph_db", fail_get_graph_db)

    health = await kernel_health.check_neo4j()

    assert health["status"] == "unhealthy"
    assert "neo4j unavailable" in health["message"]


@pytest.mark.asyncio
async def test_postgres_connection_failure_is_unhealthy(monkeypatch):
    class FailingEngine:
        def connect(self):
            raise RuntimeError("postgres unavailable")

    class FailingPostgresDatabase:
        engine = FailingEngine()

    monkeypatch.setattr(kernel_health, "postgres_db", FailingPostgresDatabase())

    health = await kernel_health.check_postgres()

    assert health["status"] == "unhealthy"
    assert "postgres unavailable" in health["message"]
