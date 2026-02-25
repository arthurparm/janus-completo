from __future__ import annotations

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
    if pending_action_id is None and not reason:
        return None
    payload: dict[str, Any] = {
        "required": True,
        "reason": reason or "requires_confirmation",
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
    if confirmation and isinstance(normalized.get("confirmation"), dict) is False:
        normalized["confirmation"] = confirmation
    if confirmation:
        normalized["requires_confirmation"] = bool(confirmation.get("required", True))
        if not normalized.get("confirmation_reason"):
            normalized["confirmation_reason"] = confirmation.get("reason")
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

