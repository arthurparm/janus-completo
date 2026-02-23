import json
import logging
from typing import Any

from langchain.tools import tool

from app.core.tools.action_module import PermissionLevel, ToolCategory, action_registry

logger = logging.getLogger(__name__)

_calendar_events: dict[str, list[dict[str, Any]]] = {}
_notes: dict[str, list[dict[str, Any]]] = {}


@tool
def list_calendar_events(user_id: str) -> str:
    """
    Lista eventos do calendário do usuário.
    Requer escopo 'calendar.read'.
    """
    events = _calendar_events.get(user_id) or []
    return json.dumps(events, ensure_ascii=False)


@tool
def create_calendar_event(user_id: str, title: str, when_ts_ms: int) -> str:
    """
    Cria um evento simples no calendário.
    Requer escopo 'calendar.write'.
    """
    ev = {"title": title, "when_ts_ms": int(when_ts_ms)}
    _calendar_events.setdefault(user_id, []).append(ev)
    return json.dumps({"status": "created", "event": ev}, ensure_ascii=False)


@tool
def send_email(user_id: str, to: str, subject: str, body: str) -> str:
    """
    Envia um email (stub) para o destinatário.
    Requer escopo 'email.send'.
    """
    logger.info("[EMAIL]", extra={"user_id": user_id, "to": to, "subject": subject})
    return json.dumps({"status": "queued", "to": to, "subject": subject}, ensure_ascii=False)


@tool
def create_note(user_id: str, title: str, content: str) -> str:
    """
    Cria uma nota textual.
    Requer escopo 'notes.write'.
    """
    note = {"title": title, "content": content[:2000]}
    _notes.setdefault(user_id, []).append(note)
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
