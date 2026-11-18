from __future__ import annotations

import argparse
from pathlib import Path

import tooling.dev as dev


def test_parse_args_doctor_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dev.py", "doctor"])
    args = dev.parse_args()

    assert args.command == "doctor"
    assert args.host == "100.89.17.105"
    assert args.backend_port == 8000
    assert args.frontend_port == 4300
    assert args.timeout == 5.0
    assert args.json_out == ""
    assert args.verify_tls is False


def test_cmd_doctor_builds_command(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], *, cwd: Path | None = None) -> None:
        captured["cmd"] = cmd
        captured["cwd"] = cwd

    monkeypatch.setattr(dev, "run", fake_run)

    args = argparse.Namespace(
        host="100.89.17.105",
        backend_port=8000,
        frontend_port=4300,
        timeout=7.5,
        json_out=str(tmp_path / "diag.json"),
        verify_tls=True,
    )
    dev.cmd_doctor(args)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert Path(cmd[0]).name.startswith("python")
    assert Path(cmd[1]).parts[-2:] == ("tooling", "quick_diagnostics.py")
    assert "--host" in cmd and "100.89.17.105" in cmd
    assert "--backend-port" in cmd and "8000" in cmd
    assert "--frontend-port" in cmd and "4300" in cmd
    assert "--timeout" in cmd and "7.5" in cmd
    assert "--json-out" in cmd
    assert "--verify-tls" in cmd
    assert captured["cwd"] == dev.REPO_ROOT


def test_parse_args_readiness_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dev.py", "readiness"])
    args = dev.parse_args()

    assert args.command == "readiness"
    assert args.baseline.endswith("documentation\\operations\\production-readiness.baseline.json")
    assert args.env_files == []
    assert args.format == "markdown"
    assert args.out == ""


def test_cmd_readiness_builds_command(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        captured["cmd"] = cmd
        captured["cwd"] = cwd

    monkeypatch.setattr(dev, "run", fake_run)

    args = argparse.Namespace(
        baseline=str(tmp_path / "baseline.json"),
        env_files=[".env.pc1.example", ".env.pc2.example"],
        format="json",
        out=str(tmp_path / "readiness.json"),
    )
    dev.cmd_readiness(args)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert Path(cmd[0]).name.startswith("python")
    assert Path(cmd[1]).parts[-2:] == ("tooling", "production_readiness.py")
    assert "--baseline" in cmd and str(tmp_path / "baseline.json") in cmd
    assert cmd.count("--env-file") == 2
    assert "--format" in cmd and "json" in cmd
    assert "--out" in cmd
    assert captured["cwd"] == dev.REPO_ROOT


def test_cmd_up_builds_compose_runtime_images(monkeypatch):
    commands: list[list[str]] = []
    envs: list[dict[str, str] | None] = []

    def fake_run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        commands.append(cmd)
        envs.append(env)
        assert cwd == dev.REPO_ROOT

    monkeypatch.setattr(dev, "ensure_env_files", lambda: None)
    monkeypatch.setattr(dev, "resolve_env_file", lambda name: name)
    monkeypatch.setattr(dev, "wait_for_health", lambda urls: None)
    monkeypatch.setattr(dev, "run", fake_run)

    dev.cmd_up()

    assert len(commands) == 2
    assert commands[0][:4] == ["docker", "compose", "-f", "docker-compose.pc2.yml"]
    assert commands[1][:4] == ["docker", "compose", "-f", "docker-compose.pc1.yml"]
    assert "--build" not in commands[0]
    assert "--build" in commands[1]
    assert envs[0] == {
        "NEO4J_HEAP_INITIAL": "512M",
        "NEO4J_HEAP_MAX": "2G",
        "NEO4J_PAGECACHE": "512M",
        "NEO4J_MEM_LIMIT": "4g",
        "NEO4J_MEMSWAP_LIMIT": "5g",
    }
    assert envs[1] == {
        "NEO4J_URI": "bolt://host.docker.internal:7687",
        "QDRANT_HOST": "host.docker.internal",
        "OLLAMA_HOST": "http://host.docker.internal:11434",
    }


def test_backend_python_supports_declared_runtime_range():
    assert dev.is_supported_backend_python((3, 11)) is True
    assert dev.is_supported_backend_python((3, 12)) is True
    assert dev.is_supported_backend_python((3, 13)) is False
    assert dev.is_supported_backend_python((3, 10)) is False


def test_cmd_qa_fails_fast_on_unsupported_python(monkeypatch):
    monkeypatch.setattr(dev, "is_supported_backend_python", lambda: False)
    monkeypatch.setattr(dev.sys, "version_info", (3, 13, 0))

    try:
        dev.cmd_qa()
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("cmd_qa should reject unsupported Python before running pytest")

    assert "Unsupported Python runtime" in message
    assert "3.11 <= Python < 3.13" in message
