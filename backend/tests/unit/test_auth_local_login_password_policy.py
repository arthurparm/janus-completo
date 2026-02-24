from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth


def test_local_login_rejects_short_password_with_422():
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/local/login",
        json={"email": "user@example.com", "password": "123"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert isinstance(payload, dict)
    assert "detail" in payload
