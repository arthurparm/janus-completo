from __future__ import annotations

from typing import Final

TERMINAL_STATUSES: Final[set[str]] = {"completed", "failed", "blocked", "cancelled"}

_ALIASES: Final[dict[str, str]] = {
    "success": "completed",
    "done": "completed",
    "complete": "completed",
    "completed": "completed",
    "failure": "failed",
    "fail": "failed",
    "failed": "failed",
    "error": "failed",
    "max_iterations_reached": "failed",
    "blocked": "blocked",
    "cancel": "cancelled",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "in_progress": "in_progress",
    "pending": "in_progress",
    "running": "in_progress",
}


def normalize_task_status(status: str | None) -> str:
    raw = str(status or "").strip().lower()
    if not raw:
        return "in_progress"
    return _ALIASES.get(raw, raw)


def is_terminal_status(status: str | None) -> bool:
    return normalize_task_status(status) in TERMINAL_STATUSES


def is_success_terminal_status(status: str | None) -> bool:
    return normalize_task_status(status) == "completed"
