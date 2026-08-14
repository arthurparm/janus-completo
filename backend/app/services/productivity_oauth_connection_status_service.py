from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.db import db
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository
from app.services.productivity_oauth_state_service import GOOGLE_PRODUCTIVITY_CONSENTS


class GoogleConnectionStatusUnavailableError(RuntimeError):
    """The locally persisted Google connection state could not be read."""


@dataclass(frozen=True, slots=True)
class GoogleConnectionStatus:
    local_status: Literal["disconnected", "configured", "inconsistent"]
    capabilities: dict[str, bool]
    provider_verified: bool


def get_google_connection_status(*, user_id: int) -> GoogleConnectionStatus:
    session = db.get_session_direct()
    try:
        token_present = (
            OAuthTokenRepository(session).get(user_id=user_id, provider="google")
            is not None
        )
        consent_repo = ConsentRepository(session)
        granted_scopes = {
            scope
            for scopes in GOOGLE_PRODUCTIVITY_CONSENTS.values()
            for scope in scopes
            if consent_repo.has_consent(user_id, scope)
        }
        capabilities = {
            capability: all(scope in granted_scopes for scope in scopes)
            for capability, scopes in GOOGLE_PRODUCTIVITY_CONSENTS.items()
        }
    except Exception as exc:
        raise GoogleConnectionStatusUnavailableError(
            "Local Google connection status is unavailable"
        ) from exc
    finally:
        session.close()

    has_capability = any(capabilities.values())
    if not token_present and not granted_scopes:
        local_status: Literal["disconnected", "configured", "inconsistent"] = (
            "disconnected"
        )
    elif token_present and has_capability:
        local_status = "configured"
    else:
        local_status = "inconsistent"

    return GoogleConnectionStatus(
        local_status=local_status,
        capabilities=capabilities,
        # This endpoint performs no provider I/O and therefore makes no remote claim.
        provider_verified=False,
    )
