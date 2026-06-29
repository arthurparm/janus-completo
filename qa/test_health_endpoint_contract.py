import pytest
from app.core.kernel import KernelState
from app.main import app, health, is_public_api_key_exempt_path
from httpx import ASGITransport, AsyncClient


def test_public_api_key_exempts_root_health_endpoints():
    assert is_public_api_key_exempt_path("/health") is True
    assert is_public_api_key_exempt_path("/healthz") is True


def test_public_api_key_health_exemption_is_not_prefix_based():
    assert is_public_api_key_exempt_path("/health/services") is False
    assert is_public_api_key_exempt_path("/healthz/details") is False


def test_public_api_key_keeps_static_prefix_exemption():
    assert is_public_api_key_exempt_path("/static/app.js") is True


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_auto_healer_step_metrics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    metrics_text = response.text
    assert "auto_healer_step_attempts_total" in metrics_text
    assert "auto_healer_step_successes_total" in metrics_text
    assert "auto_healer_step_failures_total" in metrics_text


def test_root_health_reports_degraded_when_critical_check_is_missing(monkeypatch):
    import app.main as main_module

    class DummyKernel:
        state = KernelState.HEALTHY
        degraded_dependencies = {}

    class DummyMonitor:
        health_checks = {
            "postgres": {"is_critical": True},
            "worker": {"is_critical": False},
        }
        last_results = {}

    monkeypatch.setattr(main_module.Kernel, "get_instance", lambda: DummyKernel())
    monkeypatch.setattr(main_module, "get_health_monitor", lambda: DummyMonitor())

    response = health()

    assert response["status"] == "degraded"
    assert response["dependencies"]["postgres"]["status"] == "unknown"
