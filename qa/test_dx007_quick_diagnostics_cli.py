from __future__ import annotations

from pathlib import Path

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
    assert report["topology"] == "split"
    assert report["health_checks"]["backend_health"]["url"] == "http://100.89.17.105:8000/health"
    assert report["health_checks"]["frontend_root"]["url"] == "http://100.89.17.105:4300"
    assert report["dependency_checks"]["qdrant_gateway"]["url"] == "https://100.89.17.105:9443"


def test_build_report_uses_local_dependency_targets_for_localhost():
    probed_urls: list[str] = []

    def fake_http(url: str, timeout: float, insecure_tls: bool):
        probed_urls.append(url)
        return {"ok": True, "status_code": 200, "sample": "ok"}

    def fake_tcp(host: str, port: int, timeout: float):
        return {"ok": True}

    report = build_report(
        host="localhost",
        backend_port=8000,
        frontend_port=4300,
        timeout=1.0,
        insecure_tls=True,
        config_paths=["backend/app/config.py"],
        http_probe=fake_http,
        tcp_probe=fake_tcp,
    )

    assert report["summary"]["overall_ok"] is True
    assert report["topology"] == "local"
    assert report["dependency_checks"]["neo4j_browser"]["url"] == "http://localhost:7474/browser/"
    assert report["dependency_checks"]["qdrant_health"]["url"] == "http://localhost:6333/healthz"
    assert report["dependency_checks"]["ollama_tags"]["url"] == "http://localhost:11434/api/tags"
    assert "https://localhost:9443" not in probed_urls


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


def test_build_report_marks_config_false_when_required_env_key_missing(tmp_path: Path):
    env_file = tmp_path / ".env.pc1"
    env_file.write_text(
        "POSTGRES_PASSWORD=secret\n"
        "RABBITMQ_PASSWORD=secret\n"
        "NEO4J_PASSWORD=secret\n"
        "QDRANT_API_KEY=\n"
        "OLLAMA_HOST=http://100.89.17.105:11434\n",
        encoding="utf-8",
    )

    def fake_http(url: str, timeout: float, insecure_tls: bool):
        return {"ok": True, "status_code": 200}

    def fake_tcp(host: str, port: int, timeout: float):
        return {"ok": True}

    report = build_report(
        host="100.89.17.105",
        backend_port=8000,
        frontend_port=4300,
        timeout=1.0,
        insecure_tls=True,
        config_paths=[str(env_file)],
        http_probe=fake_http,
        tcp_probe=fake_tcp,
    )

    assert report["summary"]["config_ok"] is False
    assert report["summary"]["overall_ok"] is False
    assert "QDRANT_API_KEY" in report["config_checks"][0]["missing_keys"]
    assert "AUDIT_LEDGER_HMAC_KEY" in report["config_checks"][0]["missing_keys"]
