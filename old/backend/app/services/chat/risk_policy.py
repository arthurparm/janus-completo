"""Pure chat confirmation-risk evaluation.

No repository, transport, or presentation dependency is allowed here.  This
keeps risk decisions deterministic and independently testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

_PENDING_ACTION_MARKER_RE = re.compile(
    r"(?:pending\s*action\s*id|pending[_\s-]*action[_\s-]*id)\s*[:=#-]?\s*([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_HIGH_RISK_KEYWORDS = (
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
    "destrut",
    "deletar",
    "apagar",
    "excluir",
    "remover",
    "rm -rf",
    "powershell",
    "cmd.exe",
    "shell",
)


def normalize_confirmation_reason(reason: object) -> str | None:
    if reason is None:
        return None
    text = str(reason).strip()
    if not text or text.lower() in {"none", "null", "undefined"}:
        return None
    return text


@dataclass(frozen=True)
class ConfirmationRiskAssessment:
    """Result of evaluating whether an actionable confirmation must exist."""

    requires_pending_action: bool
    reason: str | None
    high_risk_signal: bool
    pending_marker_signal: bool


def evaluate_confirmation_risk(
    *,
    message: str,
    assistant_response: str | None = None,
    understanding: Mapping[str, object] | None = None,
    existing_pending_action_id: int | None = None,
) -> ConfirmationRiskAssessment:
    """Evaluate chat confirmation risk without creating or updating state."""

    context = understanding if isinstance(understanding, Mapping) else {}
    normalized_reason = normalize_confirmation_reason(context.get("confirmation_reason"))
    lowered_message = str(message or "").lower()
    lowered_response = str(assistant_response or "").lower()
    high_risk_signal = any(
        keyword in lowered_message or keyword in lowered_response
        for keyword in _HIGH_RISK_KEYWORDS
    )
    pending_marker_signal = bool(_PENDING_ACTION_MARKER_RE.search(str(assistant_response or "")))
    high_risk_reason = str(normalized_reason or "").lower() == "high_risk"
    requires_confirmation = bool(context.get("requires_confirmation"))
    should_create = (
        existing_pending_action_id is None
        and (requires_confirmation or high_risk_signal or pending_marker_signal)
        and (high_risk_signal or pending_marker_signal or high_risk_reason)
    )
    return ConfirmationRiskAssessment(
        requires_pending_action=should_create,
        reason=(normalized_reason or "high_risk") if should_create else normalized_reason,
        high_risk_signal=high_risk_signal,
        pending_marker_signal=pending_marker_signal,
    )


def summarize_confirmation_risk(
    *,
    understanding: Mapping[str, object] | None,
    confirmation: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Build a presentation-neutral risk summary from confirmation signals."""

    if not isinstance(understanding, Mapping):
        return None
    risk = understanding.get("risk")
    if isinstance(risk, Mapping):
        if not all(isinstance(key, str) for key in risk):
            raise TypeError("Risk summary contains a non-string key")
        return {key: value for key, value in risk.items() if isinstance(key, str)}
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
