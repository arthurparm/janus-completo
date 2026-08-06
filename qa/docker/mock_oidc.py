from __future__ import annotations

import base64
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs

import jwt
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, HTTPException, Query, Request

FIXTURE = Path(os.environ.get("OIDC_FIXTURE_DIR", "/fixture"))
ISSUER = os.environ.get("OIDC_TEST_ISSUER", "https://idp.test:8443")
KID = json.loads((FIXTURE / "fixture.json").read_text(encoding="utf-8"))["kid"]
PRIVATE_KEY = serialization.load_pem_private_key(
    (FIXTURE / "signing-key.pem").read_bytes(), password=None
)
PUBLIC_NUMBERS = PRIVATE_KEY.public_key().public_numbers()
CLIENT_SECRETS = {
    "janus-admin-facade": os.environ.get(
        "OIDC_TEST_FACADE_SECRET", "integration-facade-credential"
    ),
    "janus-worker": os.environ.get(
        "OIDC_TEST_WORKER_SECRET", "integration-worker-credential"
    ),
}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _b64uint(value: int) -> str:
    size = max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


def _issue_token(
    *,
    subject: str,
    audience: str,
    scopes: str = "",
    groups: list[str] | None = None,
    client_id: str | None = None,
    expires_in: int = 300,
) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": subject,
        "iss": ISSUER,
        "aud": audience,
        "exp": now + expires_in,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "typ": "at+jwt",
    }
    if scopes:
        claims["scope"] = scopes
    if groups is not None:
        claims["groups"] = groups
    if client_id:
        claims["client_id"] = client_id
        claims["azp"] = client_id
    return jwt.encode(
        claims,
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": KID},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/.well-known/jwks.json")
async def jwks() -> dict[str, object]:
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KID,
                "n": _b64uint(PUBLIC_NUMBERS.n),
                "e": _b64uint(PUBLIC_NUMBERS.e),
            }
        ]
    }


@app.get("/test-token")
async def test_user_token(
    subject: str = Query("user-a"),
    admin: bool = Query(False),
    expired: bool = Query(False),
    audience: str = Query("janus-user-api"),
) -> dict[str, str]:
    return {
        "access_token": _issue_token(
            subject=subject,
            audience=audience,
            groups=["janus-administrators"] if admin else [],
            expires_in=-60 if expired else 300,
        ),
        "token_type": "Bearer",
    }


@app.post("/token")
async def service_token(request: Request) -> dict[str, object]:
    authorization = request.headers.get("Authorization") or ""
    if not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="invalid_client")
    try:
        client_id, secret = base64.b64decode(authorization[6:]).decode().split(":", 1)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="invalid_client") from None
    if CLIENT_SECRETS.get(client_id) != secret:
        raise HTTPException(status_code=401, detail="invalid_client")
    form = parse_qs((await request.body()).decode())
    if form.get("grant_type", [""])[0] != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    audience = form.get("audience", [""])[0]
    if audience != "janus-control-plane":
        raise HTTPException(status_code=400, detail="invalid_audience")
    scope = form.get("scope", [""])[0]
    return {
        "access_token": _issue_token(
            subject=client_id,
            audience=audience,
            scopes=scope,
            client_id=client_id,
        ),
        "token_type": "Bearer",
        "expires_in": 300,
    }
