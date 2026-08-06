from app.main import app, health
from fastapi.testclient import TestClient


def test_profile_health_routes_are_explicit_and_operational_routes_are_protected():
    client = TestClient(app)

    assert client.get("/healthz/public").status_code == 200
    assert client.get("/healthz/user").status_code == 401
    assert client.get("/healthz/control-plane").status_code == 401
    assert client.get("/health").status_code == 401
    assert client.get("/metrics").status_code == 401
    assert client.get("/healthz").status_code == 404


def test_control_plane_health_reports_degraded_when_critical_check_is_missing(monkeypatch):
    import app.main as main_module
    from app.core.kernel import KernelState

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
