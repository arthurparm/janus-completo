from app.main import app
from fastapi.testclient import TestClient


def test_oidc_config_is_the_only_public_auth_operation():
    client = TestClient(app)

    response = client.get("/api/v1/auth/oidc-config")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "issuer",
        "client_id",
        "audience",
        "scopes",
        "authorization_endpoint",
        "response_type",
        "code_challenge_method",
    }
    assert payload["response_type"] == "code"
    assert payload["code_challenge_method"] == "S256"
    assert "secret" not in str(payload).lower()


def test_legacy_token_issuance_and_provider_exchanges_are_absent():
    client = TestClient(app)
    removed = (
        ("/api/v1/auth/token", {"user_id": 1}),
        ("/api/v1/auth/local/login", {"email": "u@example.com", "password": "password"}),
        ("/api/v1/auth/local/register", {"email": "u@example.com"}),
        ("/api/v1/auth/local/refresh", {"refresh_token": "token"}),
        ("/api/v1/auth/local/request-reset", {"email": "u@example.com"}),
        ("/api/v1/auth/local/reset", {"token": "token"}),
        ("/api/v1/auth/firebase/exchange", {"token": "token"}),
        ("/api/v1/auth/supabase/exchange", {"token": "token"}),
    )

    for path, body in removed:
        assert client.post(path, json=body).status_code == 404
