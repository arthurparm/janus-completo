import json
from contextvars import ContextVar
import structlog
from typing import Any

from langchain.tools import tool

from app.core.tools.action_module import PermissionLevel, ToolCategory, action_registry

logger = structlog.get_logger(__name__)

_calendar_events_ctx: ContextVar[dict[str, list[dict[str, Any]]] | None] = ContextVar(
    "calendar_events_ctx",
    default=None,
)
_notes_ctx: ContextVar[dict[str, list[dict[str, Any]]] | None] = ContextVar(
    "notes_ctx",
    default=None,
)


def _get_context_store(
    context_store: ContextVar[dict[str, list[dict[str, Any]]] | None],
) -> dict[str, list[dict[str, Any]]]:
    store = context_store.get()
    if store is None:
        store = {}
        context_store.set(store)
    return store


def _email_domain(address: str) -> str:
    parts = (address or "").split("@", 1)
    if len(parts) != 2 or not parts[1]:
        return "unknown"
    return parts[1].lower()


def _subject_fingerprint(subject: str) -> str:
    normalized = (subject or "").strip()
    if not normalized:
        return "empty"
    return f"len:{len(normalized)}"


@tool
def list_calendar_events() -> str:
    """
    Lista eventos do calendário do usuário.
    Requer escopo 'calendar.read'.
    """
    events = _get_context_store(_calendar_events_ctx).get("default") or []
    return json.dumps(events, ensure_ascii=False)


@tool
def create_calendar_event(title: str, when_ts_ms: int) -> str:
    """
    Cria um evento simples no calendário.
    Requer escopo 'calendar.write'.
    """
    ev = {"title": title, "when_ts_ms": int(when_ts_ms)}
    _get_context_store(_calendar_events_ctx).setdefault("default", []).append(ev)
    return json.dumps({"status": "created", "event": ev}, ensure_ascii=False)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Envia um email (stub) para o destinatário.
    Requer escopo 'email.send'.
    """
    logger.info(
        "email_queued",
        to_domain=_email_domain(to),
        subject_fingerprint=_subject_fingerprint(subject),
    )
    return json.dumps({"status": "queued", "to": to, "subject": subject}, ensure_ascii=False)


@tool
def create_note(title: str, content: str) -> str:
    """
    Cria uma nota textual.
    Requer escopo 'notes.write'.
    """
    note = {"title": title, "content": content[:2000]}
    _get_context_store(_notes_ctx).setdefault("default", []).append(note)
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
    tags=["scope:email.send", "personal", "sensitive"],
)
action_registry.register(
    create_note,
    category=ToolCategory.API,
    permission_level=PermissionLevel.WRITE,
    tags=["scope:notes.write", "personal"],
)
