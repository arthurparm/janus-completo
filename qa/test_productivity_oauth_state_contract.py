from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.api.v1.endpoints import productivity
from app.core.security.actor_context import ActorContext, AuthMethod
from app.services.productivity_oauth_state_service import issue_google_oauth_state
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

    invalid_scope = _client().get(
        "/api/v1/productivity/oauth/google/start?scope=administrator"
    )
    legacy_body = _client().post(
        "/api/v1/productivity/oauth/google/start",
        json={"scopes": ["https://www.googleapis.com/auth/calendar"]},
    )
    assert invalid_scope.status_code == 422
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


def test_callback_uses_unmasked_secret_and_grants_only_verified_scope(
    oauth_config: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    token_writes: list[dict[str, object]] = []
    consent_writes: list[str] = []

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

    class _OAuthRepository:
        def upsert(self, **kwargs: object) -> None:
            token_writes.append(kwargs)

    class _ConsentRepository:
        def add_consent(self, *, scope: str, **_kwargs: object) -> None:
            consent_writes.append(scope)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: _Client())
    monkeypatch.setattr(productivity, "OAuthTokenRepository", _OAuthRepository)
    monkeypatch.setattr(productivity, "ConsentRepository", _ConsentRepository)
    monkeypatch.setattr(
        "app.core.security.egress_policy.enforce_worker_http_egress",
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
    assert token_writes[0]["access_token"] == "access"
    assert consent_writes == ["mail.send"]
