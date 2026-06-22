from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.governance.data_classification import DataClassification, classify_text


@dataclass(frozen=True)
class EnforcementDecision:
    classification: str
    allow: bool
    reason: str | None = None


def enforce_external_processing(text: str, *, provider: str) -> EnforcementDecision:
    mode = str(getattr(settings, "DATA_CLASSIFICATION_ENFORCEMENT", "off") or "off").strip().lower()
    classification = classify_text(text)
    if mode not in {"block", "strict"}:
        return EnforcementDecision(classification=classification, allow=True, reason=None)

    provider_norm = str(provider or "").strip().lower()
    internal_providers = {"ollama", "janus", "local"}
    if provider_norm in internal_providers:
        return EnforcementDecision(classification=classification, allow=True, reason=None)

    if classification in {DataClassification.PII, DataClassification.SECRET}:
        return EnforcementDecision(
            classification=classification,
            allow=False,
            reason="sensitive_data_blocked_for_external_provider",
        )

    return EnforcementDecision(classification=classification, allow=True, reason=None)

