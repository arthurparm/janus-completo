from __future__ import annotations

from app.core.memory.security import decrypt_text, encrypt_text

_ENVELOPE_PREFIX = "janus-oauth:v1:"


class OAuthTokenProtectionError(RuntimeError):
    """An OAuth credential could not be protected or recovered safely."""


def is_protected_oauth_token(value: str | None) -> bool:
    return bool(value and value.startswith(_ENVELOPE_PREFIX))


def protect_oauth_token(value: str) -> str:
    if not value:
        raise OAuthTokenProtectionError("OAuth token is empty")
    if is_protected_oauth_token(value):
        return value
    try:
        encrypted, method = encrypt_text(value, require_key=True)
    except RuntimeError as exc:
        raise OAuthTokenProtectionError("OAuth token encryption is unavailable") from exc
    if method not in {"fernet", "vault_transit"} or encrypted == value:
        raise OAuthTokenProtectionError("OAuth token encryption is unavailable")
    return f"{_ENVELOPE_PREFIX}{method}:{encrypted}"


def reveal_oauth_token(value: str | None) -> str | None:
    if value is None:
        return None
    if not is_protected_oauth_token(value):
        return value
    envelope = value[len(_ENVELOPE_PREFIX) :]
    try:
        method, encrypted = envelope.split(":", 1)
    except ValueError as exc:
        raise OAuthTokenProtectionError("OAuth token envelope is invalid") from exc
    if method not in {"fernet", "vault_transit"} or not encrypted:
        raise OAuthTokenProtectionError("OAuth token envelope is invalid")
    revealed = str(decrypt_text(encrypted, {"enc": method}))
    if not revealed or revealed == encrypted:
        raise OAuthTokenProtectionError("OAuth token decryption failed")
    return revealed
