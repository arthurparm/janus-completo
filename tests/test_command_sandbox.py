import os
import sys
from pathlib import Path

sys.path.append(os.path.join(os.getcwd(), "janus"))

import app.core.tools.command_sandbox as sandbox_module
from app.core.tools.command_sandbox import run_restricted_command, validate_command


def test_validate_command_blocks_shell_operators(monkeypatch):
    monkeypatch.setenv("CHAT_TOOL_COMMAND_ALLOWLIST", "echo,ls")
    ok, reason, _parts = validate_command("echo hello && rm -rf /tmp/x")
    assert ok is False
    assert "operators" in str(reason).lower()


def test_validate_command_blocks_executable_outside_allowlist(monkeypatch):
    monkeypatch.setenv("CHAT_TOOL_COMMAND_ALLOWLIST", "echo,ls")
    ok, reason, _parts = validate_command("python --version")
    assert ok is False
    assert "outside allowlist" in str(reason).lower()


def test_run_restricted_command_invokes_subprocess_without_shell(monkeypatch):
    monkeypatch.setenv("CHAT_TOOL_COMMAND_ALLOWLIST", "echo")
    captured = {}

    class DummyResult:
        def __init__(self):
            self.stdout = "ok"
            self.stderr = ""
            self.returncode = 0

    def fake_run(args, shell, capture_output, text, timeout, cwd, env):
        captured["args"] = args
        captured["shell"] = shell
        captured["timeout"] = timeout
        captured["cwd"] = cwd
        captured["env_path"] = env.get("PATH", "")
        return DummyResult()

    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)

    output = run_restricted_command("echo hello", timeout_seconds=17, cwd=Path(".").resolve())
    assert output == "ok"
    assert captured["args"] == ["echo", "hello"]
    assert captured["shell"] is False
    assert captured["timeout"] == 17
    assert isinstance(captured["cwd"], str)


def test_run_restricted_command_handles_timeout(monkeypatch):
    monkeypatch.setenv("CHAT_TOOL_COMMAND_ALLOWLIST", "echo")

    def fake_run(*_args, **_kwargs):
        raise sandbox_module.subprocess.TimeoutExpired(cmd="echo hello", timeout=3)

    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)
    output = run_restricted_command("echo hello", timeout_seconds=3)
    assert "tempo limite" in output.lower()
