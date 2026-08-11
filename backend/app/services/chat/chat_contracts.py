from __future__ import annotations

from typing import Any

from app.services.chat.risk_policy import (
    normalize_confirmation_reason,
    summarize_confirmation_risk,
)


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
    }


def _normalize_confirmation_reason(reason: object) -> str | None:
    normalized = normalize_confirmation_reason(reason)
    if normalized is not None and not isinstance(normalized, str):
        raise TypeError("Confirmation reason normalizer returned a non-string value")
    return normalized


def build_confirmation_payload(
    *,
    pending_action_id: int | None,
    reason: str | None,
) -> dict[str, Any] | None:
    normalized_reason = _normalize_confirmation_reason(reason)
    if pending_action_id is None and normalized_reason != "low_confidence":
        return None
    payload: dict[str, Any] = {
        "required": True,
        "reason": normalized_reason or "requires_confirmation",
    }
    if pending_action_id is None:
        payload["source"] = "heuristic"
        return payload
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
    if normalized.get("confidence") is not None:
        try:
            confidence = max(0.0, min(1.0, float(normalized["confidence"])))
        except (TypeError, ValueError):
            confidence = 0.0
        normalized["confidence"] = round(confidence, 2)
        normalized["confidence_band"] = (
            "high" if confidence >= 0.80 else "medium" if confidence >= 0.60 else "low"
        )
        normalized["low_confidence"] = confidence < 0.65
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
    risk = summarize_confirmation_risk(
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
