from __future__ import annotations

import re
from dataclasses import dataclass


class DataClassification:
    PII = "PII"
    SECRET = "SECRET"
    INTERNAL = "INTERNAL"


_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_PHONE_RE = re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{2,3}\)?[\s-]?\d{4,5}[\s-]?\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

_SECRET_RE = re.compile(
    r"(?i)\b("
    r"sk-[a-z0-9]{16,}|"
    r"ghp_[a-z0-9]{20,}|"
    r"xox[baprs]-[a-z0-9-]{20,}|"
    r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9._-]{10,}|"
    r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----"
    r")\b"
)
_PASSWORD_HINT_RE = re.compile(r"(?i)\b(password|passwd|senha|token|api[_-]?key|secret)\b")


@dataclass(frozen=True)
class RetentionDecision:
    classification: str
    retention_policy: str
    retention_days: int | None


def classify_text(text: str | None) -> str:
    value = str(text or "")
    if not value.strip():
        return DataClassification.INTERNAL

    if _SECRET_RE.search(value) or _PASSWORD_HINT_RE.search(value):
        return DataClassification.SECRET

    if (
        _EMAIL_RE.search(value)
        or _CPF_RE.search(value)
        or _CNPJ_RE.search(value)
        or _PHONE_RE.search(value)
        or _CARD_RE.search(value)
    ):
        return DataClassification.PII

    return DataClassification.INTERNAL


def default_retention_decision(classification: str) -> RetentionDecision:
    if classification == DataClassification.SECRET:
        return RetentionDecision(classification=classification, retention_policy="persistent", retention_days=None)
    if classification == DataClassification.PII:
        return RetentionDecision(classification=classification, retention_policy="days", retention_days=30)
    return RetentionDecision(classification=classification, retention_policy="days", retention_days=180)

