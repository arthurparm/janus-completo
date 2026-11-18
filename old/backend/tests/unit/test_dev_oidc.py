from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import jwt
from app import dev_oidc
from fastapi.testclient import TestClient


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def test_authorization_code_pkce_flow_is_one_time() -> None:
    client = TestClient(dev_oidc.app)
    verifier = "a" * 64
    params = {
        "client_id": "janus-spa",
        "response_type": "code",
        "redirect_uri": "http://localhost:4300/auth/callback",
        "scope": "openid profile email",
        "audience": "janus-user-api",
        "state": "state-value",
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
    }

    authorize = client.get("/authorize", params=params)
    assert authorize.status_code == 200
    assert "Continuar para o Janus" in authorize.text
    assert 'name="response_type" value="code"' in authorize.text
    assert 'name="code_challenge_method" value="S256"' in authorize.text

    confirm = client.post("/authorize/confirm", data=params, follow_redirects=False)
    assert confirm.status_code == 303
    callback = urlparse(confirm.headers["location"])
    query = parse_qs(callback.query)
    assert query["state"] == ["state-value"]
    code = query["code"][0]

    token = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "janus-spa",
            "code": code,
            "redirect_uri": "http://localhost:4300/auth/callback",
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200
    payload = token.json()
    assert payload["token_type"] == "Bearer"

    key = jwt.PyJWK.from_dict(client.get("/.well-known/jwks.json").json()["keys"][0]).key
    claims = jwt.decode(
        payload["access_token"],
        key,
        algorithms=["RS256"],
        issuer="http://localhost:8400",
        audience="janus-user-api",
    )
    assert claims["sub"] == "local-user"
    assert claims["typ"] == "at+jwt"

    replay = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "janus-spa",
            "code": code,
            "redirect_uri": "http://localhost:4300/auth/callback",
            "code_verifier": verifier,
        },
    )
    assert replay.status_code == 400


def test_authorize_rejects_unregistered_redirect_uri() -> None:
    client = TestClient(dev_oidc.app)
    response = client.get(
        "/authorize",
        params={
            "client_id": "janus-spa",
            "response_type": "code",
            "redirect_uri": "http://attacker.invalid/callback",
            "audience": "janus-user-api",
            "state": "state-value",
            "code_challenge": "a" * 43,
            "code_challenge_method": "S256",
        },
    )
    assert response.status_code == 400
