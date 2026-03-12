from __future__ import annotations

import re
from typing import Any

from app.core.memory.security import redact_pii_text_only

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
    "bearer",
)

_INLINE_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(sk-[a-z0-9]{16,})\b"),
    re.compile(r"(?i)\b(ghp_[a-z0-9]{20,})\b"),
    re.compile(r"(?i)\b(xox[baprs]-[a-z0-9-]{20,})\b"),
    re.compile(r"(?i)\b(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9._-]{10,})\b"),
)

_SENSITIVE_VALUE_MASK = "[REDACTED_SECRET]"


def _looks_sensitive_key(key: str | None) -> bool:
    if not key:
        return False
    lowered = key.lower()
    return any(hint in lowered for hint in _SENSITIVE_KEY_HINTS)


def _mask_secret_text(value: str) -> str:
    if not value:
        return value

    masked = value
    for pattern in _INLINE_SECRET_PATTERNS:
        masked = pattern.sub("[REDACTED_SECRET]", masked)

    return redact_pii_text_only(masked)


def _mask_value(value: Any) -> str:
    _ = value
    return _SENSITIVE_VALUE_MASK


def redact_sensitive_payload(value: Any, key_hint: str | None = None) -> Any:
    """
    Redacts sensitive values recursively from payloads used in logs/audit/persistence.
    """
    if isinstance(value, dict):
        return {k: redact_sensitive_payload(v, key_hint=str(k)) for k, v in value.items()}

    if isinstance(value, list):
        return [redact_sensitive_payload(item, key_hint=key_hint) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_sensitive_payload(item, key_hint=key_hint) for item in value)

    if isinstance(value, str):
        if _looks_sensitive_key(key_hint):
            return _mask_value(value)
        return _mask_secret_text(value)

    if _looks_sensitive_key(key_hint):
        return _mask_value(value)

    return value
