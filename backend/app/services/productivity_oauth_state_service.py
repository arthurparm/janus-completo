from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Literal

GoogleProductivityScope = Literal["calendar", "mail", "notes"]
GOOGLE_PRODUCTIVITY_SCOPES: dict[GoogleProductivityScope, str] = {
    "calendar": "https://www.googleapis.com/auth/calendar.events",
    "mail": "https://www.googleapis.com/auth/gmail.send",
    "notes": "https://www.googleapis.com/auth/drive.file",
}
GOOGLE_PRODUCTIVITY_CONSENTS: dict[GoogleProductivityScope, tuple[str, ...]] = {
    "calendar": ("calendar.read", "calendar.write"),
    "mail": ("mail.send",),
    "notes": ("notes.read", "notes.write"),
}


class OAuthStateError(Exception):
    """OAuth state is malformed, expired, tampered, or belongs to another actor."""


class OAuthConfigurationError(Exception):
    """Google OAuth credentials are absent or incomplete."""


@dataclass(frozen=True, slots=True)
class VerifiedOAuthState:
    actor_id: str
    scope: GoogleProductivityScope
    issued_at: int


def _secret_value(value: object) -> str:
    getter = getattr(value, "get_secret_value", None)
    return str(getter() if callable(getter) else value or "")


def resolve_google_oauth_config(config: object) -> tuple[str, str, str]:
    client_id = _secret_value(getattr(config, "GOOGLE_OAUTH_CLIENT_ID", None))
    client_secret = _secret_value(getattr(config, "GOOGLE_OAUTH_CLIENT_SECRET", None))
    redirect_uri = str(getattr(config, "GOOGLE_OAUTH_REDIRECT_URI", None) or "")
    if not client_id or not client_secret or not redirect_uri:
        raise OAuthConfigurationError("OAuth client not configured")
    return client_id, client_secret, redirect_uri


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as exc:
        raise OAuthStateError("OAuth state inválido.") from exc


def issue_google_oauth_state(
    *,
    signing_secret: str,
    actor_id: int | str,
    scope: GoogleProductivityScope,
    now: int | None = None,
) -> str:
    if not signing_secret:
        raise OAuthStateError("Segredo de assinatura OAuth ausente.")
    issued_at = int(time.time() if now is None else now)
    payload = json.dumps(
        {
            "v": 1,
            "sub": str(actor_id),
            "scope": scope,
            "iat": issued_at,
            "nonce": secrets.token_urlsafe(18),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded = _b64encode(payload)
    signature = hmac.new(
        signing_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded}.{_b64encode(signature)}"


def verify_google_oauth_state(
    state: str,
    *,
    signing_secret: str,
    actor_id: int | str,
    now: int | None = None,
    max_age_seconds: int = 600,
) -> VerifiedOAuthState:
    if not signing_secret or max_age_seconds <= 0:
        raise OAuthStateError("Configuração de validação OAuth inválida.")
    try:
        encoded, supplied_signature = state.split(".", 1)
    except ValueError as exc:
        raise OAuthStateError("OAuth state inválido.") from exc
    expected_signature = hmac.new(
        signing_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(_b64decode(supplied_signature), expected_signature):
        raise OAuthStateError("OAuth state adulterado.")
    try:
        payload = json.loads(_b64decode(encoded))
        version = int(payload["v"])
        subject = str(payload["sub"])
        scope = str(payload["scope"])
        issued_at = int(payload["iat"])
        nonce = str(payload["nonce"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OAuthStateError("OAuth state inválido.") from exc
    if version != 1 or scope not in GOOGLE_PRODUCTIVITY_SCOPES or not nonce:
        raise OAuthStateError("OAuth state inválido.")
    if subject != str(actor_id):
        raise OAuthStateError("OAuth state pertence a outro usuário.")
    current = int(time.time() if now is None else now)
    if issued_at > current + 30 or current - issued_at > max_age_seconds:
        raise OAuthStateError("OAuth state expirado.")
    return VerifiedOAuthState(
        actor_id=subject,
        scope=scope,
        issued_at=issued_at,
    )
