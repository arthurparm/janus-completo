from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth
from app.config import settings
from app.core.security.auth_rate_limiter import reset_auth_rate_limit_store


class _RepoStub:
    def get_by_email(self, _email: str):
        return None

    def get_by_username(self, _username: str):
        return None

    def is_admin(self, _user_id: int) -> bool:
        return False


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.dependency_overrides[auth.get_user_repo] = lambda _request=None: _RepoStub()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_local_login_rate_limit_returns_429(monkeypatch):
    reset_auth_rate_limit_store()
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "AUTH_RATE_LIMITS",
        {"auth.local_login": {"max_attempts": 2, "window_seconds": 60}},
    )
    client = _build_client()

    payload = {"email": "u@example.com", "password": "12345678"}
    first = client.post("/api/v1/auth/local/login", json=payload)
    second = client.post("/api/v1/auth/local/login", json=payload)
    third = client.post("/api/v1/auth/local/login", json=payload)

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert "Retry-After" in third.headers


def test_issue_token_rate_limit_returns_429(monkeypatch):
    reset_auth_rate_limit_store()
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "AUTH_RATE_LIMITS",
        {"auth.token": {"max_attempts": 1, "window_seconds": 60}},
    )
    client = _build_client()

    payload = {"user_id": 10, "expires_in": 60}
    first = client.post("/api/v1/auth/token", json=payload, headers={"X-Actor-User-Id": "10"})
    second = client.post("/api/v1/auth/token", json=payload, headers={"X-Actor-User-Id": "10"})

    assert first.status_code == 200
    assert second.status_code == 429
