from __future__ import annotations

from tooling.quick_diagnostics import build_report


def test_build_report_uses_target_host_and_ports():
    def fake_http(url: str, timeout: float, insecure_tls: bool):
        assert timeout == 2.5
        assert insecure_tls is True
        return {"ok": True, "status_code": 200, "sample": "ok"}

    def fake_tcp(host: str, port: int, timeout: float):
        assert timeout == 2.5
        return {"ok": True}

    report = build_report(
        host="100.89.17.105",
        backend_port=8000,
        frontend_port=4300,
        timeout=2.5,
        insecure_tls=True,
        config_paths=["backend/app/config.py"],
        http_probe=fake_http,
        tcp_probe=fake_tcp,
    )

    assert report["summary"]["overall_ok"] is True
    assert report["health_checks"]["backend_health"]["url"] == "http://100.89.17.105:8000/health"
    assert report["health_checks"]["frontend_root"]["url"] == "http://100.89.17.105:4300"
    assert report["dependency_checks"]["qdrant_gateway"]["url"] == "https://100.89.17.105:9443"


def test_build_report_marks_overall_false_when_dependency_fails():
    def fake_http(url: str, timeout: float, insecure_tls: bool):
        if "11434" in url:
            return {"ok": False, "error": "connection refused"}
        return {"ok": True, "status_code": 200}

    def fake_tcp(host: str, port: int, timeout: float):
        return {"ok": True}

    report = build_report(
        host="100.89.17.105",
        backend_port=8000,
        frontend_port=4300,
        timeout=1.0,
        insecure_tls=True,
        config_paths=["backend/app/config.py"],
        http_probe=fake_http,
        tcp_probe=fake_tcp,
    )

    assert report["dependency_checks"]["ollama_tags"]["ok"] is False
    assert report["summary"]["deps_http_ok"] is False
    assert report["summary"]["overall_ok"] is False

