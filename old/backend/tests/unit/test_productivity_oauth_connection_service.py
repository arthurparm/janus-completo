from __future__ import annotations

from datetime import datetime

import pytest

from app.db import db
from app.repositories.user_repository import ConsentRepository
from app.services import productivity_oauth_connection_service as service


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed += 1


class _EmptyQuery:
    def filter(self, *_args: object) -> _EmptyQuery:
        return self

    def first(self) -> None:
        return None


class _RepositorySession(_Session):
    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    def query(self, _model: object) -> _EmptyQuery:
        return _EmptyQuery()

    def add(self, _model: object) -> None:
        return None

    def flush(self) -> None:
        self.flushes += 1

    def refresh(self, _model: object) -> None:
        return None


def test_consent_repository_can_join_an_outer_transaction() -> None:
    session = _RepositorySession()

    ConsentRepository(session).add_consent(
        user_id=7,
        scope="mail.read",
        commit=False,
    )

    assert session.commits == 0
    assert session.flushes == 1


def test_google_oauth_connection_commits_token_and_consents_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    token_writes: list[dict[str, object]] = []
    consent_writes: list[dict[str, object]] = []

    class _TokenRepository:
        def __init__(self, supplied_session: object) -> None:
            assert supplied_session is session

        def upsert(self, **kwargs: object) -> None:
            token_writes.append(kwargs)

    class _ConsentRepository:
        def __init__(self, supplied_session: object) -> None:
            assert supplied_session is session

        def add_consent(self, **kwargs: object) -> None:
            consent_writes.append(kwargs)

    monkeypatch.setattr(db, "get_session_direct", lambda: session)
    monkeypatch.setattr(service, "OAuthTokenRepository", _TokenRepository)
    monkeypatch.setattr(service, "ConsentRepository", _ConsentRepository)

    service.persist_google_oauth_connection(
        user_id=7,
        scope="mail",
        access_token="access",
        refresh_token="refresh",
        expires_at=datetime(2026, 8, 14),
    )

    assert token_writes[0]["commit"] is False
    assert [write["scope"] for write in consent_writes] == ["mail.read", "mail.send"]
    assert all(write["commit"] is False for write in consent_writes)
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed == 1


def test_google_oauth_connection_rolls_back_all_writes_on_consent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    consent_attempts = 0

    class _TokenRepository:
        def __init__(self, _session: object) -> None:
            return None

        def upsert(self, **_kwargs: object) -> None:
            return None

    class _ConsentRepository:
        def __init__(self, _session: object) -> None:
            return None

        def add_consent(self, **_kwargs: object) -> None:
            nonlocal consent_attempts
            consent_attempts += 1
            if consent_attempts == 2:
                raise RuntimeError("consent persistence failed")

    monkeypatch.setattr(db, "get_session_direct", lambda: session)
    monkeypatch.setattr(service, "OAuthTokenRepository", _TokenRepository)
    monkeypatch.setattr(service, "ConsentRepository", _ConsentRepository)

    with pytest.raises(service.OAuthConnectionPersistenceError):
        service.persist_google_oauth_connection(
            user_id=7,
            scope="mail",
            access_token="access",
            refresh_token="refresh",
            expires_at=None,
        )

    assert consent_attempts == 2
    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closed == 1
