from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.api.v1.endpoints import productivity
from app.core.security.actor_context import ActorContext, AuthMethod
from app.services.oauth_token_security_service import OAuthTokenProtectionError
from app.services.productivity_oauth_connection_status_service import (
    GoogleConnectionStatus,
    GoogleConnectionStatusUnavailableError,
)
from app.services.productivity_oauth_disconnect_service import (
    GoogleDisconnectPersistenceError,
    GoogleDisconnectResult,
)
from app.services.productivity_oauth_state_registry_service import (
    OAuthStateAlreadyConsumedError,
    OAuthStateRegistryUnavailableError,
)
from app.services.productivity_oauth_state_service import issue_google_oauth_state
from app.services.productivity_oauth_token_exchange_service import (
    GoogleOAuthCodeRejectedError,
    GoogleOAuthExchangeBlockedError,
    GoogleOAuthExchangeProviderError,
    GoogleOAuthExchangeTimeoutError,
)
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr


def _client(actor_id: int = 1) -> TestClient:
    app = FastAPI()

    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def inject_actor(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.actor_context = ActorContext.authenticated(
            actor_id=actor_id,
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="oauth-state-test",
            issuer="https://test-idp.invalid",
            subject=f"user-{actor_id}",
        )
        return await call_next(request)

    app.include_router(productivity.router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture  # type: ignore[untyped-decorator]
def oauth_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        productivity.settings, "GOOGLE_OAUTH_CLIENT_ID", SecretStr("real-client-id")
    )
    monkeypatch.setattr(
        productivity.settings,
        "GOOGLE_OAUTH_CLIENT_SECRET",
        SecretStr("real-client-secret"),
    )
    monkeypatch.setattr(
        productivity.settings,
        "GOOGLE_OAUTH_REDIRECT_URI",
        "https://janus.example/oauth/google/callback",
    )
    monkeypatch.setattr(
        productivity,
        "register_google_oauth_state",
        AsyncMock(),
    )
    monkeypatch.setattr(
        productivity,
        "consume_google_oauth_state",
        AsyncMock(),
    )


def test_oauth_start_returns_the_signed_state_used_in_authorize_url(
    oauth_config: None,
) -> None:
    response = _client().get("/api/v1/productivity/oauth/google/start?scope=calendar")

    assert response.status_code == 200
    body = response.json()
    query = parse_qs(urlparse(body["authorize_url"]).query)
    assert query["state"] == [body["state"]]
    assert query["client_id"] == ["real-client-id"]
    assert query["scope"] == ["https://www.googleapis.com/auth/calendar.events"]
    assert "real-client-secret" not in body["authorize_url"]
    register = productivity.register_google_oauth_state
    assert isinstance(register, AsyncMock)
    register.assert_awaited_once_with(body["state"])

    invalid_scope = _client().get(
        "/api/v1/productivity/oauth/google/start?scope=administrator"
    )
    disconnected_notes_scope = _client().get(
        "/api/v1/productivity/oauth/google/start?scope=notes"
    )
    legacy_body = _client().post(
        "/api/v1/productivity/oauth/google/start",
        json={"scopes": ["https://www.googleapis.com/auth/calendar"]},
    )
    assert invalid_scope.status_code == 422
    assert disconnected_notes_scope.status_code == 422
    assert legacy_body.status_code == 422


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "state",
    [
        "unsigned-state",
        issue_google_oauth_state(
            signing_secret="real-client-secret",
            actor_id=2,
            scope="mail",
        ),
    ],
)
def test_callback_rejects_invalid_or_cross_user_state_before_network(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", pytest.fail)

    response = _client(actor_id=1).post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "code", "state": state},
    )

    assert response.status_code == 400


def test_oauth_start_fails_closed_when_replay_registry_is_unavailable(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        productivity,
        "register_google_oauth_state",
        AsyncMock(side_effect=OAuthStateRegistryUnavailableError("redis unavailable")),
    )

    response = _client().get("/api/v1/productivity/oauth/google/start?scope=calendar")

    assert response.status_code == 503
    assert response.json()["detail"] == "OAuth replay protection unavailable"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error", "expected_status"),
    [
        (OAuthStateAlreadyConsumedError("already consumed"), 400),
        (OAuthStateRegistryUnavailableError("redis unavailable"), 503),
    ],
)
def test_callback_rejects_replay_or_registry_failure_before_network(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    monkeypatch.setattr(
        productivity,
        "consume_google_oauth_state",
        AsyncMock(side_effect=error),
    )
    monkeypatch.setattr(httpx, "AsyncClient", pytest.fail)
    state = issue_google_oauth_state(
        signing_secret="real-client-secret",
        actor_id=1,
        scope="calendar",
    )

    response = _client(actor_id=1).post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "code", "state": state},
    )

    assert response.status_code == expected_status


def test_callback_uses_unmasked_secret_and_grants_only_verified_scope(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    connection_writes: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 60,
            }

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, _url: str, **kwargs: object) -> _Response:
            captured.update(kwargs)
            return _Response()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: _Client())
    monkeypatch.setattr(
        productivity,
        "persist_google_oauth_connection",
        lambda **kwargs: connection_writes.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.productivity_oauth_token_exchange_service.enforce_worker_http_egress",
        lambda url, **_kwargs: url,
    )
    state = issue_google_oauth_state(
        signing_secret="real-client-secret",
        actor_id=1,
        scope="mail",
    )

    response = _client(actor_id=1).post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "code", "state": state},
    )

    assert response.status_code == 200
    assert captured["data"] == {
        "code": "code",
        "client_id": "real-client-id",
        "client_secret": "real-client-secret",
        "redirect_uri": "https://janus.example/oauth/google/callback",
        "grant_type": "authorization_code",
    }
    assert connection_writes[0]["user_id"] == 1
    assert connection_writes[0]["scope"] == "mail"
    assert connection_writes[0]["access_token"] == "access"
    consume = productivity.consume_google_oauth_state
    assert isinstance(consume, AsyncMock)
    consume.assert_awaited_once_with(state)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error", "expected_status"),
    [
        (GoogleOAuthCodeRejectedError("rejected"), 400),
        (GoogleOAuthExchangeBlockedError("blocked"), 503),
        (GoogleOAuthExchangeProviderError("provider"), 502),
        (GoogleOAuthExchangeTimeoutError("timeout"), 504),
    ],
)
def test_callback_distinguishes_user_rejection_from_provider_failure(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    exchange = AsyncMock(side_effect=error)
    monkeypatch.setattr(productivity, "exchange_google_authorization_code", exchange)
    monkeypatch.setattr(productivity, "persist_google_oauth_connection", pytest.fail)
    state = issue_google_oauth_state(
        signing_secret="real-client-secret",
        actor_id=1,
        scope="calendar",
    )

    response = _client(actor_id=1).post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "code", "state": state},
    )

    assert response.status_code == expected_status
    exchange.assert_awaited_once()
    consume = productivity.consume_google_oauth_state
    assert isinstance(consume, AsyncMock)
    consume.assert_awaited_once_with(state)


def test_manual_refresh_uses_shared_actor_scoped_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = SimpleNamespace(refresh_token="refresh-token")
    repository = SimpleNamespace(get=lambda **_kwargs: token)
    refresh = AsyncMock(return_value="new-access")
    monkeypatch.setattr(productivity, "OAuthTokenRepository", lambda: repository)
    monkeypatch.setattr(productivity, "refresh_google_access_token", refresh)

    response = _client(actor_id=7).post(
        "/api/v1/productivity/oauth/google/refresh"
    )

    assert response.status_code == 200
    refresh.assert_awaited_once_with(repo=repository, token=token, user_id=7)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error", "expected_status"),
    [
        (httpx.ConnectError("provider"), 502),
        (httpx.TimeoutException("timeout"), 504),
    ],
)
def test_manual_refresh_maps_shared_service_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    token = SimpleNamespace(refresh_token="refresh-token")
    repository = SimpleNamespace(get=lambda **_kwargs: token)
    monkeypatch.setattr(productivity, "OAuthTokenRepository", lambda: repository)
    monkeypatch.setattr(
        productivity,
        "refresh_google_access_token",
        AsyncMock(side_effect=error),
    )

    response = _client(actor_id=7).post(
        "/api/v1/productivity/oauth/google/refresh"
    )

    assert response.status_code == expected_status


def test_manual_refresh_fails_closed_when_persisted_token_cannot_be_decrypted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Repository:
        def get(self, **_kwargs: object) -> None:
            raise OAuthTokenProtectionError("decryption failed")

    monkeypatch.setattr(productivity, "OAuthTokenRepository", _Repository)

    response = _client(actor_id=7).post(
        "/api/v1/productivity/oauth/google/refresh"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "OAuth token protection unavailable"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "result",
    [
        GoogleDisconnectResult(
            status="disconnected",
            provider_revoked=True,
            retry_required=False,
        ),
        GoogleDisconnectResult(
            status="local_disconnected",
            provider_revoked=False,
            retry_required=True,
            warning="retry provider revocation",
        ),
    ],
)
def test_disconnect_returns_truthful_full_or_partial_state(
    monkeypatch: pytest.MonkeyPatch,
    result: GoogleDisconnectResult,
) -> None:
    disconnect = AsyncMock(return_value=result)
    monkeypatch.setattr(productivity, "disconnect_google_productivity", disconnect)

    response = _client(actor_id=7).post(
        "/api/v1/productivity/oauth/google/disconnect"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": result.status,
        "provider_revoked": result.provider_revoked,
        "retry_required": result.retry_required,
        "warning": result.warning,
    }
    disconnect.assert_awaited_once_with(user_id=7)


def test_disconnect_reports_local_persistence_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        productivity,
        "disconnect_google_productivity",
        AsyncMock(side_effect=GoogleDisconnectPersistenceError("database unavailable")),
    )

    response = _client(actor_id=7).post(
        "/api/v1/productivity/oauth/google/disconnect"
    )

    assert response.status_code == 503


def test_connection_status_is_actor_scoped_and_truthful(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_reader = Mock(
        return_value=GoogleConnectionStatus(
            local_status="configured",
            capabilities={"calendar": True, "mail": False},
            provider_verified=False,
        )
    )
    monkeypatch.setattr(productivity, "get_google_connection_status", status_reader)

    response = _client(actor_id=7).get(
        "/api/v1/productivity/oauth/google/status"
    )

    assert response.status_code == 200
    assert response.json() == {
        "local_status": "configured",
        "capabilities": {"calendar": True, "mail": False},
        "provider_verified": False,
    }
    status_reader.assert_called_once_with(user_id=7)


def test_connection_status_reports_storage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        productivity,
        "get_google_connection_status",
        Mock(side_effect=GoogleConnectionStatusUnavailableError("database unavailable")),
    )

    response = _client(actor_id=7).get(
        "/api/v1/productivity/oauth/google/status"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Google connection status unavailable"
