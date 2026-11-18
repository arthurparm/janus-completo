"""Loopback-only OIDC provider for the local Docker development stack.

This module is deliberately not mounted in the production application router.
It runs as its own Compose service and binds to 127.0.0.1 on the host.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

PUBLIC_ORIGIN = os.getenv("OIDC_DEV_PUBLIC_ORIGIN", "http://localhost:8400").rstrip("/")
CLIENT_ID = os.getenv("OIDC_DEV_CLIENT_ID", "janus-spa")
AUDIENCE = os.getenv("OIDC_DEV_AUDIENCE", "janus-user-api")
ADMIN_GROUP = os.getenv("OIDC_DEV_ADMIN_GROUP", "janus-administrators")
ALLOWED_REDIRECTS = frozenset(
    value.strip()
    for value in os.getenv(
        "OIDC_DEV_REDIRECT_URIS",
        "http://localhost:4300/auth/callback,http://127.0.0.1:4300/auth/callback",
    ).split(",")
    if value.strip()
)
CODE_TTL_SECONDS = 120
TOKEN_TTL_SECONDS = 900

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_NUMBERS = _PRIVATE_KEY.public_key().public_numbers()
_PUBLIC_DER = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
_KID = hashlib.sha256(_PUBLIC_DER).hexdigest()[:16]


@dataclass(frozen=True)
class AuthorizationCode:
    client_id: str
    redirect_uri: str
    code_challenge: str
    subject: str
    audience: str
    expires_at: float


_codes: dict[str, AuthorizationCode] = {}

app = FastAPI(title="Janus Local Development IdP", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4300", "http://127.0.0.1:4300"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _b64uint(value: int) -> str:
    size = max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


def _issue_token(*, subject: str, audience: str, scopes: str, client_id: str | None = None) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": subject,
        "iss": PUBLIC_ORIGIN,
        "aud": audience,
        "exp": now + TOKEN_TTL_SECONDS,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "typ": "at+jwt",
        "scope": scopes,
    }
    if client_id:
        claims.update({"client_id": client_id, "azp": client_id})
    else:
        claims.update(
            {
                "email": "local-user@janus.invalid",
                "email_verified": True,
                "name": "Janus Local User",
                "preferred_username": "local-user",
                "groups": [ADMIN_GROUP] if ADMIN_GROUP else [],
            }
        )
    return jwt.encode(claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KID})


def _required(values: dict[str, list[str]], name: str) -> str:
    value = values.get(name, [""])[0].strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"missing_{name}")
    return value


def _validate_authorization(values: dict[str, list[str]]) -> dict[str, str]:
    client_id = _required(values, "client_id")
    redirect_uri = _required(values, "redirect_uri")
    response_type = _required(values, "response_type")
    code_challenge = _required(values, "code_challenge")
    code_challenge_method = _required(values, "code_challenge_method")
    state = _required(values, "state")
    audience = _required(values, "audience")
    if client_id != CLIENT_ID or response_type != "code":
        raise HTTPException(status_code=400, detail="invalid_client_or_response_type")
    if redirect_uri not in ALLOWED_REDIRECTS:
        raise HTTPException(status_code=400, detail="invalid_redirect_uri")
    if code_challenge_method != "S256" or len(code_challenge) < 43:
        raise HTTPException(status_code=400, detail="invalid_pkce_challenge")
    if audience != AUDIENCE:
        raise HTTPException(status_code=400, detail="invalid_audience")
    return {
        "client_id": client_id,
        "response_type": response_type,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
        "audience": audience,
        "scope": values.get("scope", ["openid profile email"])[0],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "local-development-only"}


@app.get("/.well-known/openid-configuration")
async def discovery() -> dict[str, object]:
    return {
        "issuer": PUBLIC_ORIGIN,
        "authorization_endpoint": f"{PUBLIC_ORIGIN}/authorize",
        "token_endpoint": f"{PUBLIC_ORIGIN}/token",
        "jwks_uri": f"{PUBLIC_ORIGIN}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
    }


@app.get("/.well-known/jwks.json")
async def jwks() -> dict[str, object]:
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": _KID,
                "n": _b64uint(_PUBLIC_NUMBERS.n),
                "e": _b64uint(_PUBLIC_NUMBERS.e),
            }
        ]
    }


@app.get("/authorize", response_class=HTMLResponse)
async def authorize(request: Request) -> HTMLResponse:
    values = parse_qs(request.url.query)
    validated = _validate_authorization(values)
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(value)}">'
        for key, value in validated.items()
    )
    return HTMLResponse(
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<title>Janus Local Identity</title><style>
:root{color-scheme:dark}body{margin:0;min-height:100vh;display:grid;place-items:center;
font:16px/1.5 Inter,ui-sans-serif,system-ui,sans-serif;background:#0a0a0a;color:#eaf2f8;
position:relative;overflow:hidden}
body::before{content:"";position:fixed;inset:0;z-index:-1;
background:radial-gradient(ellipse 60% 45% at 15% 20%,rgba(69,195,255,.10),transparent 55%),
radial-gradient(ellipse 55% 40% at 85% 80%,rgba(35,213,161,.08),transparent 55%)}
.card{position:relative;width:min(92vw,460px);padding:2.25rem;border-radius:24px;
background:rgba(255,255,255,.05);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
border:1px solid rgba(255,255,255,.1)}
.eyebrow{color:#45c3ff;letter-spacing:.08em;font-size:.75rem;font-weight:600;text-transform:uppercase}
h1{margin:.6rem 0;font-size:1.5rem;font-weight:600;letter-spacing:-.02em}
p{color:#b3c1cc;line-height:1.55}
.identity{padding:1rem 1.1rem;border-radius:14px;background:rgba(255,255,255,.04);
border:1px solid rgba(255,255,255,.08);margin:1.5rem 0}
.identity strong{font-weight:600}.identity span{color:#8ea2b0;font-size:.9rem}
button{width:100%;padding:.9rem 1rem;border:0;border-radius:9999px;background:#fff;
color:#0a0a0a;font-weight:600;font-size:.9rem;cursor:pointer;transition:transform .2s ease}
button:hover{transform:translateY(-1px)}
small{display:block;margin-top:1rem;color:#8ea2b0;font-size:.75rem}</style></head>
<body><main class="card"><div class="eyebrow">JANUS // AMBIENTE LOCAL</div>
<h1>Identidade de desenvolvimento</h1><p>Este provedor existe somente no computador local e usa Authorization Code com PKCE.</p>
<div class="identity"><strong>Janus Local User</strong><br><span>local-user@janus.invalid</span></div>
<form method="post" action="/authorize/confirm">"""
        + hidden
        + """<button type="submit">Continuar para o Janus</button></form>
<small>Nenhuma senha real é solicitada ou armazenada.</small></main></body></html>""",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/authorize/confirm")
async def authorize_confirm(request: Request) -> RedirectResponse:
    values = parse_qs((await request.body()).decode())
    validated = _validate_authorization(values)
    code = secrets.token_urlsafe(32)
    _codes[code] = AuthorizationCode(
        client_id=validated["client_id"],
        redirect_uri=validated["redirect_uri"],
        code_challenge=validated["code_challenge"],
        subject="local-user",
        audience=validated["audience"],
        expires_at=time.time() + CODE_TTL_SECONDS,
    )
    location = f'{validated["redirect_uri"]}?{urlencode({"code": code, "state": validated["state"]})}'
    return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store"})


@app.post("/token")
async def token(request: Request) -> JSONResponse:
    values = parse_qs((await request.body()).decode())
    grant_type = _required(values, "grant_type")
    if grant_type == "authorization_code":
        code = _required(values, "code")
        authorization = _codes.pop(code, None)
        if authorization is None or authorization.expires_at < time.time():
            raise HTTPException(status_code=400, detail="invalid_grant")
        client_id = _required(values, "client_id")
        redirect_uri = _required(values, "redirect_uri")
        verifier = _required(values, "code_verifier")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        if (
            client_id != authorization.client_id
            or redirect_uri != authorization.redirect_uri
            or not hmac.compare_digest(challenge, authorization.code_challenge)
        ):
            raise HTTPException(status_code=400, detail="invalid_grant")
        access_token = _issue_token(
            subject=authorization.subject,
            audience=authorization.audience,
            scopes="openid profile email",
        )
        return JSONResponse(
            {"access_token": access_token, "token_type": "Bearer", "expires_in": TOKEN_TTL_SECONDS},
            headers={"Cache-Control": "no-store"},
        )
    if grant_type == "client_credentials":
        authorization_header = request.headers.get("Authorization", "")
        if not authorization_header.startswith("Basic "):
            raise HTTPException(status_code=401, detail="invalid_client")
        try:
            client_id, secret = base64.b64decode(authorization_header[6:]).decode().split(":", 1)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=401, detail="invalid_client") from None
        expected_secret = os.getenv("OIDC_DEV_FACADE_SECRET", "")
        if client_id != "janus-admin-facade" or not expected_secret or not hmac.compare_digest(secret, expected_secret):
            raise HTTPException(status_code=401, detail="invalid_client")
        audience = values.get("audience", ["janus-control-plane"])[0]
        if audience != "janus-control-plane":
            raise HTTPException(status_code=400, detail="invalid_audience")
        access_token = _issue_token(
            subject=client_id,
            audience=audience,
            scopes=values.get("scope", [""])[0],
            client_id=client_id,
        )
        return JSONResponse(
            {"access_token": access_token, "token_type": "Bearer", "expires_in": TOKEN_TTL_SECONDS},
            headers={"Cache-Control": "no-store"},
        )
    raise HTTPException(status_code=400, detail="unsupported_grant_type")
