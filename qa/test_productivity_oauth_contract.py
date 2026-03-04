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
        json={"user_id": 1, "code": "abc"},
    )
    assert resp.status_code == 404


def test_legacy_refresh_route_removed():
    client = _client()
    resp = client.post(
        LEGACY_REFRESH_PATH,
        json={"user_id": 1, "provider": "google"},
    )
    assert resp.status_code == 404


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
    assert resp.status_code == 401
