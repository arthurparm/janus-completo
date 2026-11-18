from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED_SECRET = "[REDACTED_SECRET]"
REDACTED_PII = "[REDACTED_PII]"
REDACTED_PAYMENT = "[REDACTED_PAYMENT]"
REDACTION_FAILED = "[REDACTION_FAILED]"

_SENSITIVE_KEY_HINTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "access_key",
    "private_key",
    "client_secret",
    "session",
    "cvv",
    "cvc",
)
_PII_KEY_HINTS = (
    "user_id",
    "actor_id",
    "owner_id",
    "email",
    "phone",
    "cpf",
    "cnpj",
    "full_name",
    "display_name",
    "address",
)
_PAYMENT_KEY_HINTS = ("card", "cvv", "cvc", "payment", "bank_account")

_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), REDACTED_SECRET),
    (re.compile(r"(?i)\b(?:bearer\s+)?eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9._-]{10,}\b"), REDACTED_SECRET),
    (re.compile(r"(?i)\b(?:sk-|gh[pousr]_|xox[baprs]-)[a-z0-9_-]{12,}\b"), REDACTED_SECRET),
    (re.compile(r"(?i)([?&](?:token|key|secret|password|signature|sig)=)[^&#\s]+"), r"\1" + REDACTED_SECRET),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), REDACTED_PAYMENT),
    (re.compile(r"(?i)\b(?:cvv|cvc)\s*[:=]\s*\d{3,4}\b"), REDACTED_PAYMENT),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), REDACTED_PII),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), REDACTED_PII),
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), REDACTED_PII),
    (re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}(?!\d)"), REDACTED_PII),
)


def _looks_sensitive_key(key: str | None) -> bool:
    lowered = str(key or "").lower()
    return any(
        hint in lowered
        for hint in _SENSITIVE_KEY_HINTS + _PII_KEY_HINTS + _PAYMENT_KEY_HINTS
    )


def _placeholder_for_key(key: str | None) -> str:
    lowered = str(key or "").lower()
    if any(hint in lowered for hint in _PAYMENT_KEY_HINTS):
        return REDACTED_PAYMENT
    if any(hint in lowered for hint in _PII_KEY_HINTS):
        return REDACTED_PII
    return REDACTED_SECRET


def _redact_text(value: str) -> str:
    result = value
    for pattern, replacement in _TEXT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _redact(value: Any, key_hint: str | None, seen: set[int]) -> Any:
    if _looks_sensitive_key(key_hint):
        return _placeholder_for_key(key_hint)
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in seen:
            return REDACTION_FAILED
        seen.add(identity)
        try:
            return {str(key): _redact(child, str(key), seen) for key, child in value.items()}
        finally:
            seen.remove(identity)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        identity = id(value)
        if identity in seen:
            return REDACTION_FAILED
        seen.add(identity)
        try:
            redacted = [_redact(child, key_hint, seen) for child in value]
            return tuple(redacted) if isinstance(value, tuple) else redacted
        finally:
            seen.remove(identity)
    if _looks_sensitive_key(key_hint):
        return REDACTED_SECRET
    return value


def redact_sensitive_payload(value: Any, key_hint: str | None = None) -> Any:
    """Recursively redact every logging/audit payload; failure never returns the source value."""
    try:
        return _redact(value, key_hint, set())
    except Exception:
        return REDACTION_FAILED
