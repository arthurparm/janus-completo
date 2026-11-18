from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.v1.endpoints import consents
from app.core.security.actor_context import ActorContext, AuthMethod


class _Session:
    def __init__(self, consent):
        self.consent = consent
        self.committed = False
        self.closed = False

    def query(self, _model):
        return self

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.consent

    def commit(self):
        self.committed = True

    def refresh(self, _value):
        return None

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_revoke_consent_persists_timezone_aware_utc_timestamp(monkeypatch):
    consent = SimpleNamespace(
        id=7,
        user_id="user-1",
        scope="calendar.write",
        resource=None,
        granted="True",
        created_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        revoked_at=None,
    )
    session = _Session(consent)
    monkeypatch.setattr(consents, "_get_session", lambda: session)
    actor = ActorContext.authenticated(
        actor_id="user-1",
        roles=("USER",),
        auth_method=AuthMethod.OIDC,
        trace_id="trace-consent",
    )
    request = SimpleNamespace(state=SimpleNamespace(actor_context=actor))

    response = await consents.revoke_consent(7, request)

    assert response.granted == "False"
    assert consent.revoked_at.tzinfo is timezone.utc
    assert session.committed is True
    assert session.closed is True
