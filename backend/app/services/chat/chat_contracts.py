from __future__ import annotations

import json
import re
from typing import Any


def chat_http_error_detail(
    *,
    code: str,
    message: str,
    category: str,
    retryable: bool,
    http_status: int,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "code": code,
        "message": message,
        "category": category,
        "retryable": retryable,
        "http_status": http_status,
        "details": details or {},
    }
    return {
        "message": message,
        "code": code,
        "category": category,
        "retryable": retryable,
        "http_status": http_status,
        "details": details or {},
        "error": payload,
    }


def chat_sse_error_payload(
    *,
    code: str,
    message: str,
    category: str,
    retryable: bool,
    http_status: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "category": category,
        "retryable": retryable,
        "http_status": http_status,
        "details": details or {},
        # Legacy compat for current frontend parser.
        "error": message,
    }


_PENDING_ACTION_ID_RE = re.compile(r"Pending action id:\s*(\d+)", re.IGNORECASE)
_HIGH_RISK_FALLBACK_KEYWORDS = (
    "deploy",
    "production",
    "produção",
    "prod ",
    "prod-",
    "delete",
    "drop",
    "truncate",
    "shutdown",
    "reset",
    "wipe",
)


def extract_pending_action_id_from_text(text: str | None) -> int | None:
    if not text:
        return None
    match = _PENDING_ACTION_ID_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _normalize_confirmation_reason(reason: Any) -> str | None:
    if reason is None:
        return None
    text = str(reason).strip()
    if not text:
        return None
    if text.lower() in {"none", "null", "undefined"}:
        return None
    return text


def maybe_create_fallback_pending_action(
    *,
    user_id: str | None,
    message: str,
    conversation_id: str | None = None,
    existing_pending_action_id: int | None = None,
    understanding: dict[str, Any] | None = None,
) -> tuple[int | None, str | None]:
    if existing_pending_action_id is not None:
        return existing_pending_action_id, _normalize_confirmation_reason(
            (understanding or {}).get("confirmation_reason") if isinstance(understanding, dict) else None
        )
    if not user_id:
        return None, None
    if not isinstance(understanding, dict):
        return None, None
    if not bool(understanding.get("requires_confirmation")):
        return None, None

    lowered = str(message or "").lower()
    if not any(keyword in lowered for keyword in _HIGH_RISK_FALLBACK_KEYWORDS):
        return None, _normalize_confirmation_reason(understanding.get("confirmation_reason"))

    reason = _normalize_confirmation_reason(understanding.get("confirmation_reason")) or "high_risk"
    try:
        from app.repositories.pending_action_repository import PendingActionRepository

        repo = PendingActionRepository()
        pending = repo.create(
            user_id=str(user_id),
            tool_name="chat_high_risk_request",
            args_json=json.dumps(
                {
                    "source": "chat_confirmation_fallback",
                    "conversation_id": conversation_id,
                    "message": message,
                    "risk_reason": reason,
                },
                ensure_ascii=False,
            ),
            run_id=None,
            cycle=None,
        )
        pending_id = getattr(pending, "id", None)
        if pending_id is None:
            return None, reason
        return int(pending_id), reason
    except Exception:
        return None, reason


def summarize_risk_from_message_and_confirmation(
    *,
    understanding: dict[str, Any] | None,
    confirmation: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(understanding, dict):
        return None
    risk = understanding.get("risk")
    if isinstance(risk, dict):
        return risk
    requires_confirmation = bool(understanding.get("requires_confirmation"))
    if not requires_confirmation and not confirmation:
        return None
    reason = str(understanding.get("confirmation_reason") or "")
    level = "high" if reason == "high_risk" else ("medium" if requires_confirmation else "low")
    summary = (
        "Ação classificada como alto risco; confirmação obrigatória."
        if reason == "high_risk"
        else (
            "Baixa confiança para executar ação; confirmação recomendada."
            if reason == "low_confidence"
            else "Ação requer confirmação antes de prosseguir."
        )
    )
    return {
        "level": level,
        "source": "heuristic",
        "summary": summary,
        "requires_confirmation": requires_confirmation,
    }


def build_confirmation_payload(
    *,
    pending_action_id: int | None,
    reason: str | None,
) -> dict[str, Any] | None:
    normalized_reason = _normalize_confirmation_reason(reason)
    # Demo contract: only surface actionable confirmation when a real pending action exists.
    if pending_action_id is None:
        return None
    payload: dict[str, Any] = {
        "required": True,
        "reason": normalized_reason or "requires_confirmation",
    }
    if pending_action_id is not None:
        payload.update(
            {
                "source": "pending_actions_sql",
                "pending_action_id": pending_action_id,
                "approve_endpoint": f"/api/v1/pending_actions/action/{pending_action_id}/approve",
                "reject_endpoint": f"/api/v1/pending_actions/action/{pending_action_id}/reject",
            }
        )
    return payload


def normalize_understanding_payload(
    understanding: dict[str, Any] | None,
    *,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(understanding, dict):
        return None
    normalized = dict(understanding)
    normalized_reason = _normalize_confirmation_reason(normalized.get("confirmation_reason"))
    if normalized_reason is None:
        normalized.pop("confirmation_reason", None)
    else:
        normalized["confirmation_reason"] = normalized_reason
    if confirmation and isinstance(normalized.get("confirmation"), dict) is False:
        normalized["confirmation"] = confirmation
    if confirmation:
        normalized["requires_confirmation"] = bool(confirmation.get("required", True))
        if not normalized.get("confirmation_reason"):
            normalized["confirmation_reason"] = confirmation.get("reason")
    elif normalized.get("requires_confirmation") and not normalized_reason:
        # No actionable confirmation and no valid reason: prevent false positives in UI/contracts.
        normalized["requires_confirmation"] = False
    risk = summarize_risk_from_message_and_confirmation(
        understanding=normalized,
        confirmation=confirmation,
    )
    if risk and not isinstance(normalized.get("risk"), dict):
        normalized["risk"] = risk
    return normalized


def build_agent_state(
    *,
    stream_phase: str | None = None,
    understanding: dict[str, Any] | None = None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    state = None
    if confirmation and confirmation.get("required"):
        state = "waiting_confirmation"
    elif isinstance(understanding, dict) and understanding.get("low_confidence"):
        state = "low_confidence"
    elif stream_phase:
        state = stream_phase
    if not state:
        return None
    payload: dict[str, Any] = {"state": state}
    if isinstance(understanding, dict):
        if understanding.get("confidence_band"):
            payload["confidence_band"] = understanding.get("confidence_band")
        if understanding.get("requires_confirmation") is not None:
            payload["requires_confirmation"] = bool(understanding.get("requires_confirmation"))
        if understanding.get("confirmation_reason"):
            payload["reason"] = understanding.get("confirmation_reason")
    return payload
