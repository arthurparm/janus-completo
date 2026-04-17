import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.productivity import router as productivity_router

LEGACY_CALLBACK_PATH = "/api/v1/productivity/oauth/google" + "/legacy/callback"
LEGACY_REFRESH_PATH = "/api/v1/productivity/oauth/google" + "/legacy/refresh"


def _client() -> TestClient:
    app = FastAPI()
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
    assert resp.status_code == 400

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
