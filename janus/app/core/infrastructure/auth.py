import base64
import hashlib
import hmac
import json
import time

from fastapi import Request

from app.config import settings


def _sign(payload: dict) -> str:
    secret = (settings.AUTH_JWT_SECRET or "janus_dev_secret").encode("utf-8")
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
