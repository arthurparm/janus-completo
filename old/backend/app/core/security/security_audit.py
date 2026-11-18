from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import structlog

from app.core.security.actor_context import ActorContext
from app.core.security.redaction import redact_sensitive_payload

logger = structlog.get_logger(__name__)


def _actor_reference(actor: ActorContext | None) -> str | None:
    if actor is None:
        return None
    return "actor:" + hashlib.sha256(actor.actor_id.encode("utf-8")).hexdigest()[:16]


def _spool_path() -> Path:
    configured = os.getenv("SECURITY_AUDIT_OUTBOX_PATH", "").strip()
    return Path(configured or "outputs/security/security-audit-outbox.jsonl")


def record_security_event(
    *,
    endpoint: str,
    action: str,
    status: str,
    event: dict[str, object],
    user_id: int | None = None,
    tool: str | None = None,
    trace_id: str | None = None,
) -> bool:
    """Record a security event in the ledger or its durable local outbox."""
    redacted_event = redact_sensitive_payload(event)
    try:
        from app.repositories.observability_repository import record_audit_event_direct

        recorded = record_audit_event_direct(
            endpoint=endpoint,
            action=action,
            status=status,
            user_id=user_id,
            tool=tool,
            trace_id=trace_id,
            details_json=redacted_event,
        )
        if recorded:
            return True
        logger.error("security_audit_primary_sink_failed", error_type="event_not_recorded")
    except Exception as exc:
        logger.error("security_audit_primary_sink_failed", error_type=type(exc).__name__)

    path = _spool_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(redacted_event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except Exception as exc:
        logger.critical("security_audit_outbox_failed", error_type=type(exc).__name__)
        return False


def record_security_denial(
    *,
    method: str,
    route: str,
    reason: str,
    trace_id: str,
    actor: ActorContext | None,
    status_code: int,
) -> None:
    record_security_event(
        endpoint=route,
        action="security_access_denied",
        status="blocked",
        trace_id=trace_id,
        event={
            "event": "security_access_denied",
            "method": method,
            "route": route,
            "reason": reason,
            "trace_id": trace_id,
            "actor_reference": _actor_reference(actor),
            "status_code": status_code,
        },
    )
