from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import settings
from app.core.tools import command_sandbox, external_cli_tools


def test_validate_command_rejects_shell_chaining():
    ok, reason, parts = command_sandbox.validate_command("git status && whoami")

    assert ok is False
    assert "blocked" in (reason or "").lower()
    assert parts is None


def test_validate_command_rejects_multiline():
    ok, reason, parts = command_sandbox.validate_command("git status\nwhoami")

    assert ok is False
    assert "multiline" in (reason or "").lower()
    assert parts is None


def test_validate_command_rejects_executable_outside_allowlist(monkeypatch):
    monkeypatch.setattr(command_sandbox, "get_allowed_commands", lambda: {"git"})

    ok, reason, parts = command_sandbox.validate_command("python script.py")

    assert ok is False
    assert "outside allowlist" in (reason or "").lower()
    assert parts is None


def test_external_cli_runs_without_shell_and_keeps_prompt_as_single_argument(monkeypatch):
    calls: dict[str, object] = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(settings, "EXTERNAL_CLI_ENABLED", True)
    monkeypatch.setattr(settings, "WORKSPACE_ROOT", "/tmp")
    monkeypatch.setattr(external_cli_tools, "_get_cli_path", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(external_cli_tools.subprocess, "run", fake_run)

    result = external_cli_tools.codex_exec.func("review this && rm -rf /", model="o3")

    assert result == "ok"
    assert calls["args"] == [
        "/usr/bin/codex",
        "exec",
        "-C",
        str(Path("/tmp").resolve()),
        "-m",
        "o3",
        "review this && rm -rf /",
    ]
    assert calls["kwargs"]["shell"] is False


def test_external_cli_reports_non_zero_exit_code(monkeypatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(settings, "EXTERNAL_CLI_ENABLED", True)
    monkeypatch.setattr(external_cli_tools.subprocess, "run", fake_run)

    result = external_cli_tools._run_command(["/usr/bin/codex", "exec", "hello"])

    assert "boom" in result
    assert "2" in result
