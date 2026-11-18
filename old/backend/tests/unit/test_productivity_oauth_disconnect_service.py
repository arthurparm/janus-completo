from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import httpx
import pytest

from app.db import db
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository
from app.services import productivity_oauth_disconnect_service as service


class _Response:
    def __init__(self, status_code: int, payload: dict[str, object] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, object]:
        return self._payload


def _token_repository(token: object | None) -> Callable[[], SimpleNamespace]:
    return lambda: SimpleNamespace(get=lambda **_kwargs: token)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("response", "expected_provider_revoked"),
    [
        (_Response(200), True),
        (_Response(400, {"error": "invalid_token"}), True),
    ],
)
async def test_disconnect_revokes_locally_then_deletes_token_after_google_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    response: _Response,
    expected_provider_revoked: bool,
) -> None:
    local_calls: list[dict[str, object]] = []
    captured: dict[str, object] = {}
    token = SimpleNamespace(access_token="access", refresh_token="refresh")

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> _Response:
            captured["url"] = url
            captured.update(kwargs)
            return response

    monkeypatch.setattr(service, "OAuthTokenRepository", _token_repository(token))
    monkeypatch.setattr(
        service,
        "_revoke_local_google_access",
        lambda **kwargs: local_calls.append(kwargs),
    )
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())

    result = await service.disconnect_google_productivity(user_id=7)

    assert result.status == "disconnected"
    assert result.provider_revoked is expected_provider_revoked
    assert result.retry_required is False
    assert local_calls == [
        {"user_id": 7, "delete_token": False},
        {"user_id": 7, "delete_token": True},
    ]
    assert captured["data"] == {"token": "refresh"}
    assert captured["url"] == "https://oauth2.googleapis.com/revoke"


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_disconnect_keeps_encrypted_token_for_retry_when_google_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_calls: list[dict[str, object]] = []
    token = SimpleNamespace(access_token="access", refresh_token="refresh")

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> _Response:
            return _Response(500)

    monkeypatch.setattr(service, "OAuthTokenRepository", _token_repository(token))
    monkeypatch.setattr(
        service,
        "_revoke_local_google_access",
        lambda **kwargs: local_calls.append(kwargs),
    )
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())

    result = await service.disconnect_google_productivity(user_id=7)

    assert result.status == "local_disconnected"
    assert result.provider_revoked is False
    assert result.retry_required is True
    assert result.warning
    assert local_calls == [{"user_id": 7, "delete_token": False}]


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_disconnect_keeps_encrypted_token_for_retry_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_calls: list[dict[str, object]] = []
    token = SimpleNamespace(access_token="access", refresh_token="refresh")

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> _Response:
            raise httpx.ReadTimeout("Google revocation timed out")

    monkeypatch.setattr(service, "OAuthTokenRepository", _token_repository(token))
    monkeypatch.setattr(
        service,
        "_revoke_local_google_access",
        lambda **kwargs: local_calls.append(kwargs),
    )
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())

    result = await service.disconnect_google_productivity(user_id=7)

    assert result.status == "local_disconnected"
    assert result.retry_required is True
    assert local_calls == [{"user_id": 7, "delete_token": False}]


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_disconnect_blocks_local_effects_when_egress_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_calls: list[dict[str, object]] = []
    token = SimpleNamespace(access_token="access", refresh_token="refresh")
    monkeypatch.setattr(service, "OAuthTokenRepository", _token_repository(token))
    monkeypatch.setattr(
        service,
        "_revoke_local_google_access",
        lambda **kwargs: local_calls.append(kwargs),
    )
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(httpx, "AsyncClient", pytest.fail)

    result = await service.disconnect_google_productivity(user_id=7)

    assert result.status == "local_disconnected"
    assert result.retry_required is True
    assert result.warning == "Google revocation blocked by egress policy"
    assert local_calls == [{"user_id": 7, "delete_token": False}]


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_disconnect_without_stored_token_is_idempotent_and_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_calls: list[dict[str, object]] = []
    monkeypatch.setattr(service, "OAuthTokenRepository", _token_repository(None))
    monkeypatch.setattr(
        service,
        "_revoke_local_google_access",
        lambda **kwargs: local_calls.append(kwargs),
    )
    monkeypatch.setattr(httpx, "AsyncClient", pytest.fail)

    result = await service.disconnect_google_productivity(user_id=7)

    assert result.status == "disconnected"
    assert result.provider_revoked is None
    assert result.retry_required is False
    assert local_calls == [{"user_id": 7, "delete_token": False}]


def test_local_disconnect_is_one_transaction_for_consents_and_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

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

    session = _Session()

    class _ConsentRepository:
        def __init__(self, supplied_session: object) -> None:
            assert supplied_session is session

        def revoke_consent(self, _user_id: int, scope: str, **kwargs: object) -> None:
            calls.append((scope, kwargs))

    class _TokenRepository:
        def __init__(self, supplied_session: object) -> None:
            assert supplied_session is session

        def delete(self, **kwargs: object) -> None:
            calls.append(("token", kwargs))

    monkeypatch.setattr(db, "get_session_direct", lambda: session)
    monkeypatch.setattr(service, "ConsentRepository", _ConsentRepository)
    monkeypatch.setattr(service, "OAuthTokenRepository", _TokenRepository)

    service._revoke_local_google_access(user_id=7, delete_token=True)

    assert [name for name, _kwargs in calls] == [
        "calendar.read",
        "calendar.write",
        "mail.read",
        "mail.send",
        "token",
    ]
    assert all(kwargs["commit"] is False for _name, kwargs in calls)
    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed == 1


class _ExistingQuery:
    def __init__(self, value: object) -> None:
        self.value = value

    def filter(self, *_args: object) -> _ExistingQuery:
        return self

    def first(self) -> object:
        return self.value


class _RepositorySession:
    def __init__(self) -> None:
        self.value = SimpleNamespace(granted=True)
        self.commits = 0
        self.flushes = 0
        self.deleted: list[object] = []

    def query(self, _model: object) -> _ExistingQuery:
        return _ExistingQuery(self.value)

    def delete(self, value: object) -> None:
        self.deleted.append(value)

    def commit(self) -> None:
        self.commits += 1

    def flush(self) -> None:
        self.flushes += 1


def test_repositories_can_revoke_inside_outer_disconnect_transaction() -> None:
    consent_session = _RepositorySession()
    token_session = _RepositorySession()

    assert ConsentRepository(consent_session).revoke_consent(
        7, "mail.read", commit=False
    )
    assert OAuthTokenRepository(token_session).delete(
        7, "google", commit=False
    )

    assert consent_session.commits == token_session.commits == 0
    assert consent_session.flushes == token_session.flushes == 1
    assert len(consent_session.deleted) == len(token_session.deleted) == 1
