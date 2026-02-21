import base64
import hashlib
import hmac
import json
import secrets
import time

import structlog
from fastapi import Request

from app.config import settings

logger = structlog.get_logger(__name__)
_DEV_FALLBACK_SECRET = secrets.token_urlsafe(32)
_DEV_SECRET_WARNING_EMITTED = False


def _get_signing_secret() -> bytes:
    global _DEV_SECRET_WARNING_EMITTED

    configured = (settings.AUTH_JWT_SECRET or "").strip()
    if configured:
        return configured.encode("utf-8")

    if str(settings.ENVIRONMENT).lower() == "production":
        raise RuntimeError(
            "AUTH_JWT_SECRET é obrigatório em produção. Defina uma chave forte no ambiente."
        )

    if not _DEV_SECRET_WARNING_EMITTED:
        logger.warning(
            "AUTH_JWT_SECRET ausente fora de produção; usando segredo efêmero apenas nesta execução."
        )
        _DEV_SECRET_WARNING_EMITTED = True

    return _DEV_FALLBACK_SECRET.encode("utf-8")


def _sign(payload: dict) -> str:
    secret = _get_signing_secret()
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(secret, data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def create_token(user_id: int, expires_in: int | None = None) -> str:
    exp = int(time.time()) + int(expires_in or settings.AUTH_JWT_EXPIRES_SECONDS)
    payload = {"user_id": int(user_id), "exp": exp}
    sig = _sign(payload)
    body = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"{body}.{sig}"


def verify_token(token: str) -> int | None:
    try:
        if "." not in token:
            return None
        body, sig = token.split(".", 1)
        padded = body + "=" * (-len(body) % 4)
        payload_json = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(payload_json.decode("utf-8"))
        if _sign(payload) != sig:
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return int(payload.get("user_id"))
    except Exception:
        return None


def get_actor_user_id(request: Request) -> int | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        uid = verify_token(token)
        if uid is not None:
            return uid
    xuid = request.headers.get("X-User-Id")
    try:
        if xuid:
            return int(xuid)
    except Exception:
        return None
    return None
