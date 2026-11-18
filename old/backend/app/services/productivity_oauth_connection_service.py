from __future__ import annotations

from datetime import datetime

from app.db import db
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository
from app.services.oauth_token_security_service import OAuthTokenProtectionError
from app.services.productivity_oauth_state_service import (
    GOOGLE_PRODUCTIVITY_CONSENTS,
    GoogleProductivityScope,
)


class OAuthConnectionPersistenceError(RuntimeError):
    """The token and its derived consents could not be committed atomically."""


def persist_google_oauth_connection(
    *,
    user_id: int,
    scope: GoogleProductivityScope,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime | None,
) -> None:
    session = db.get_session_direct()
    try:
        OAuthTokenRepository(session).upsert(
            user_id=user_id,
            provider="google",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            commit=False,
        )
        consent_repo = ConsentRepository(session)
        for consent_scope in GOOGLE_PRODUCTIVITY_CONSENTS[scope]:
            consent_repo.add_consent(
                user_id=user_id,
                scope=consent_scope,
                granted=True,
                expires_at=None,
                commit=False,
            )
        session.commit()
    except OAuthTokenProtectionError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise OAuthConnectionPersistenceError(
            "Google OAuth connection persistence failed"
        ) from exc
    finally:
        session.close()
