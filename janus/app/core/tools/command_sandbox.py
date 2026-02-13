from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from app.config import settings

_SHELL_OPERATOR_MARKERS = ("&&", "||", ";", "|", ">", "<", "`", "$(")
_DEFAULT_ALLOWED_COMMANDS = (
    "echo,pwd,ls,cat,head,tail,wc,grep,find,python,pytest,git,date,whoami"
)
_DEFAULT_BLOCKLIST_TOKENS = (
    "rm -rf,del /f,format ,shutdown,reboot,powershell -enc,curl |,wget |,nc ,netcat "
)


def _parse_csv_set(raw: str) -> set[str]:
    return {item.strip().lower() for item in str(raw or "").split(",") if item.strip()}


def get_allowed_commands() -> set[str]:
    return _parse_csv_set(os.getenv("CHAT_TOOL_COMMAND_ALLOWLIST", _DEFAULT_ALLOWED_COMMANDS))


def get_blocked_command_tokens() -> set[str]:
    return _parse_csv_set(os.getenv("CHAT_TOOL_COMMAND_BLOCKLIST", _DEFAULT_BLOCKLIST_TOKENS))


def _has_blocked_operators(command: str) -> bool:
    return any(marker in command for marker in _SHELL_OPERATOR_MARKERS)


def _parse_command(command: str) -> list[str]:
    return shlex.split(command, posix=os.name != "nt")


def validate_command(command: str) -> tuple[bool, str | None, list[str] | None]:
    if not isinstance(command, str) or not command.strip():
        return False, "Command must be a non-empty string.", None

    normalized = command.strip()
    if "\n" in normalized or "\r" in normalized:
        return False, "Multiline command is not allowed.", None
    if len(normalized) > 600:
        return False, "Command exceeds maximum allowed length.", None
    if _has_blocked_operators(normalized):
        return False, "Shell chaining/redirection operators are blocked.", None

    lowered = normalized.lower()
    for token in get_blocked_command_tokens():
        if token and token in lowered:
            return False, f"Command blocked by token: {token}", None

    try:
        parts = _parse_command(normalized)
    except Exception as exc:
        return False, f"Invalid command syntax: {exc}", None

    if not parts:
        return False, "Command could not be parsed.", None

    executable = Path(parts[0]).name.lower()
    allowed = get_allowed_commands()
    if allowed and executable not in allowed:
        allowed_preview = ", ".join(sorted(allowed)[:12])
        return (
            False,
            f"Executable '{executable}' is outside allowlist. Allowed examples: {allowed_preview}",
            None,
        )

    return True, None, parts


def run_restricted_command(
    command: str,
    *,
    timeout_seconds: int = 30,
    cwd: Path | None = None,
) -> str:
    ok, reason, parts = validate_command(command)
    if not ok or not parts:
        return f"Erro: {reason}"

    effective_cwd = cwd or Path(settings.WORKSPACE_ROOT).resolve()
    if not effective_cwd.exists():
        effective_cwd = Path(".").resolve()

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
    }

    try:
        result = subprocess.run(
            parts,
            shell=False,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
            cwd=str(effective_cwd),
            env=env,
        )
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        combined = output
        if stderr:
            combined = f"{combined}\nSTDERR: {stderr}".strip()
        if result.returncode != 0:
            combined = f"{combined}\nExit code: {result.returncode}".strip()

        max_chars = int(getattr(settings, "EXTERNAL_CLI_MAX_OUTPUT_CHARS", 20000))
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n...[output truncated]"
        return combined or "(comando executado sem output)"
    except subprocess.TimeoutExpired:
        return f"Erro: O comando excedeu o tempo limite de {timeout_seconds}s."
    except Exception as exc:
        return f"Erro ao executar comando em modo restrito: {exc}"
