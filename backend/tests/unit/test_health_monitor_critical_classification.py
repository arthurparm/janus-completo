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
