import pytest

from app.core.monitoring import health_monitor


@pytest.mark.asyncio
async def test_check_llm_router_health_reports_healthy(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm.resilience.get_circuit_breaker_snapshot",
        lambda: {
            "ollama": {"state": "CLOSED", "failure_count": 0, "last_failure_time": None},
            "openai": {"state": "CLOSED", "failure_count": 0, "last_failure_time": None},
            "unknown": {"state": "CLOSED", "failure_count": 0, "last_failure_time": None},
        },
    )
    monkeypatch.setattr(
        "app.core.llm.resilience.get_llm_pool_summary",
        lambda: {"pool_keys": 2, "pool_total_instances": 5},
    )

    result = await health_monitor.check_llm_router_health()

    assert result["status"] == "healthy"
    assert result["details"] == {"open_circuits": 0, "pool_instances": 5}


@pytest.mark.asyncio
async def test_check_llm_router_health_reports_degraded_and_unhealthy(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm.resilience.get_llm_pool_summary",
        lambda: {"pool_keys": 1, "pool_total_instances": 1},
    )

    monkeypatch.setattr(
        "app.core.llm.resilience.get_circuit_breaker_snapshot",
        lambda: {
            "ollama": {"state": "OPEN", "failure_count": 3, "last_failure_time": 1.0},
            "openai": {"state": "CLOSED", "failure_count": 0, "last_failure_time": None},
            "unknown": {"state": "CLOSED", "failure_count": 0, "last_failure_time": None},
        },
    )
    degraded = await health_monitor.check_llm_router_health()
    assert degraded["status"] == "degraded"
    assert degraded["details"]["open_circuits"] == 1
    assert degraded["details"]["pool_instances"] == 1

    monkeypatch.setattr(
        "app.core.llm.resilience.get_circuit_breaker_snapshot",
        lambda: {
            "ollama": {"state": "OPEN", "failure_count": 3, "last_failure_time": 1.0},
            "openai": {"state": "OPEN", "failure_count": 4, "last_failure_time": 1.0},
            "unknown": {"state": "OPEN", "failure_count": 1, "last_failure_time": 1.0},
        },
    )
    unhealthy = await health_monitor.check_llm_router_health()
    assert unhealthy["status"] == "unhealthy"
    assert unhealthy["details"]["open_circuits"] == 3
