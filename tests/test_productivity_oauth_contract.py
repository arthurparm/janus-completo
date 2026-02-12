import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.api.v1.endpoints.productivity import router as productivity_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(productivity_router, prefix="/api/v1")
    return TestClient(app)


def test_legacy_callback_returns_410_with_guidance():
    client = _client()
    resp = client.post(
        "/api/v1/productivity/oauth/google/legacy/callback",
        json={"user_id": 1, "code": "abc"},
    )
    assert resp.status_code == 410
    assert "/api/v1/productivity/oauth/google/callback" in resp.json()["detail"]


def test_legacy_refresh_returns_410_with_guidance():
    client = _client()
    resp = client.post(
        "/api/v1/productivity/oauth/google/legacy/refresh",
        json={"user_id": 1, "provider": "google"},
    )
    assert resp.status_code == 410
    assert "/api/v1/productivity/oauth/google/refresh" in resp.json()["detail"]


def test_canonical_callback_route_still_exists():
    client = _client()
    resp = client.post(
        "/api/v1/productivity/oauth/google/callback",
        json={"code": "abc", "state": "user:1:scope:calendar"},
    )
    assert resp.status_code == 401


def test_canonical_refresh_route_still_exists():
    client = _client()
    resp = client.post("/api/v1/productivity/oauth/google/refresh", params={"user_id": 1})
    assert resp.status_code == 403
