from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.security.egress_policy import enforce_worker_http_egress
from app.db import db
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository
from app.services.productivity_oauth_state_service import GOOGLE_PRODUCTIVITY_CONSENTS

_GOOGLE_REVOCATION_URL = "https://oauth2.googleapis.com/revoke"
_GOOGLE_CONSENT_SCOPES = tuple(
    scope
    for capability_scopes in GOOGLE_PRODUCTIVITY_CONSENTS.values()
    for scope in capability_scopes
)


class GoogleDisconnectPersistenceError(RuntimeError):
    """Local Google access could not be revoked transactionally."""


@dataclass(frozen=True, slots=True)
class GoogleDisconnectResult:
    status: Literal["disconnected", "local_disconnected"]
    provider_revoked: bool | None
    retry_required: bool
    warning: str | None = None


def _revoke_local_google_access(*, user_id: int, delete_token: bool) -> None:
    session = db.get_session_direct()
    try:
        consent_repo = ConsentRepository(session)
        for scope in _GOOGLE_CONSENT_SCOPES:
            consent_repo.revoke_consent(user_id, scope, commit=False)
        if delete_token:
            OAuthTokenRepository(session).delete(
                user_id=user_id,
                provider="google",
                commit=False,
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise GoogleDisconnectPersistenceError(
            "Local Google disconnect persistence failed"
        ) from exc
    finally:
        session.close()


def _google_reported_already_revoked(response: httpx.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    return isinstance(payload, dict) and payload.get("error") == "invalid_token"


async def disconnect_google_productivity(*, user_id: int) -> GoogleDisconnectResult:
    token = OAuthTokenRepository().get(user_id=user_id, provider="google")

    # Human control is immediate even while the external provider is unavailable.
    _revoke_local_google_access(user_id=user_id, delete_token=False)
    if token is None:
        return GoogleDisconnectResult(
            status="disconnected",
            provider_revoked=None,
            retry_required=False,
        )

    revocation_token = token.refresh_token or token.access_token
    allowed_url = enforce_worker_http_egress(
        _GOOGLE_REVOCATION_URL,
        tool="google_productivity_disconnect",
    )
    if not allowed_url:
        return GoogleDisconnectResult(
            status="local_disconnected",
            provider_revoked=False,
            retry_required=True,
            warning="Google revocation blocked by egress policy",
        )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                allowed_url,
                data={"token": revocation_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        provider_revoked = response.status_code == 200 or _google_reported_already_revoked(
            response
        )
    except httpx.HTTPError:
        provider_revoked = False

    if not provider_revoked:
        return GoogleDisconnectResult(
            status="local_disconnected",
            provider_revoked=False,
            retry_required=True,
            warning="Google revocation failed; retry is required",
        )

    _revoke_local_google_access(user_id=user_id, delete_token=True)
    return GoogleDisconnectResult(
        status="disconnected",
        provider_revoked=True,
        retry_required=False,
    )
