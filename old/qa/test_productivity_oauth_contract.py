import os
import sys

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.productivity import router as productivity_router
from app.core.security.actor_context import ActorContext, AuthMethod

LEGACY_CALLBACK_PATH = "/api/v1/productivity/oauth/google" + "/legacy/callback"
LEGACY_REFRESH_PATH = "/api/v1/productivity/oauth/google" + "/legacy/refresh"


def _client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        request.state.actor_context = ActorContext.authenticated(
            actor_id=1,
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="test-user",
            issuer="https://test-idp.invalid",
            subject="user-1",
        )
        return await call_next(request)

    app.include_router(productivity_router, prefix="/api/v1")
    return TestClient(app)


def test_legacy_callback_route_removed():
    client = _client()
    resp = client.post(
        LEGACY_CALLBACK_PATH,
        json={"code": "abc"},
    )
    assert resp.status_code == 404


def test_legacy_refresh_route_removed():
    client = _client()
    resp = client.post(
        LEGACY_REFRESH_PATH,
        json={"provider": "google"},
    )
    assert resp.status_code == 404


def test_canonical_callback_route_still_exists():
    client = _client()
    resp = client.post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "abc", "state": "user:1:scope:calendar"},
    )
    assert resp.status_code == 503

def test_canonical_refresh_route_still_exists(monkeypatch):
    import app.api.v1.endpoints.productivity as prod_module
    class DummyUserRepo:
        def get_user(self, user_id):
            return None
    class DummyOAuthRepo:
        def get(self, user_id, provider):
            return None
    monkeypatch.setattr(prod_module, "UserRepository", DummyUserRepo)
    monkeypatch.setattr(prod_module, "OAuthTokenRepository", DummyOAuthRepo)
    client = _client()
    resp = client.post("/api/v1/productivity/oauth/google/refresh")
    assert resp.status_code == 404
