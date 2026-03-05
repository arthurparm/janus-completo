import json
import os
import structlog
from typing import Any

from langchain.tools import tool

from app.core.tools.action_module import PermissionLevel, ToolCategory, action_registry
from app.core.infrastructure.filesystem_manager import get_workspace_dir

logger = structlog.get_logger(__name__)

def _get_user_file_path(user_id: str, prefix: str) -> str:
    safe_user_id = "".join(c for c in user_id if c.isalnum())
    prod_dir = get_workspace_dir() / "productivity"
    prod_dir.mkdir(parents=True, exist_ok=True)
    return str(prod_dir / f"{prefix}_{safe_user_id}.json")

def _load_data(filepath: str) -> list[dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_data(filepath: str, data: list[dict[str, Any]]):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

@tool
def list_calendar_events(user_id: str) -> str:
    """
    Lista eventos do calendário do usuário.
    Requer escopo 'calendar.read'.
    """
    filepath = _get_user_file_path(user_id, "calendar")
    events = _load_data(filepath)
    return json.dumps(events, ensure_ascii=False)


@tool
def create_calendar_event(user_id: str, title: str, when_ts_ms: int) -> str:
    """
    Cria um evento simples no calendário.
    Requer escopo 'calendar.write'.
    """
    filepath = _get_user_file_path(user_id, "calendar")
    events = _load_data(filepath)
    ev = {"title": title, "when_ts_ms": int(when_ts_ms)}
    events.append(ev)
    _save_data(filepath, events)
    return json.dumps({"status": "created", "event": ev}, ensure_ascii=False)


@tool
def send_email(user_id: str, to: str, subject: str, body: str) -> str:
    """
    Envia um email (stub) para o destinatário.
    Requer escopo 'email.send'.
    """
    # Remove to e subject do extra logger para previnir vazamento de PII/LGPD
    logger.info("[EMAIL]", extra={"user_id": user_id})
    return json.dumps({"status": "queued", "to": to, "subject": subject}, ensure_ascii=False)


@tool
def create_note(user_id: str, title: str, content: str) -> str:
    """
    Cria uma nota textual.
    Requer escopo 'notes.write'.
    """
    filepath = _get_user_file_path(user_id, "notes")
    notes = _load_data(filepath)
    note = {"title": title, "content": content[:2000]}
    notes.append(note)
    _save_data(filepath, notes)
    return json.dumps({"status": "saved", "note": note}, ensure_ascii=False)


# Registro com metadados e escopos nas tags
action_registry.register(
    list_calendar_events,
    category=ToolCategory.API,
    permission_level=PermissionLevel.READ_ONLY,
    tags=["scope:calendar.read", "personal"],
)
action_registry.register(
    create_calendar_event,
    category=ToolCategory.API,
    permission_level=PermissionLevel.WRITE,
    tags=["scope:calendar.write", "personal"],
)
action_registry.register(
    send_email,
    category=ToolCategory.API,
    permission_level=PermissionLevel.DANGEROUS,
    tags=["scope:mail.send", "personal", "sensitive"],
)
action_registry.register(
    create_note,
    category=ToolCategory.API,
    permission_level=PermissionLevel.WRITE,
    tags=["scope:notes.write", "personal"],
)
