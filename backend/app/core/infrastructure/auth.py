from __future__ import annotations

import secrets
import time
import uuid
from typing import Any, cast

import jwt
import structlog
from fastapi import Request

from app.config import settings
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

logger = structlog.get_logger(__name__)
_DEV_FALLBACK_SECRET = secrets.token_urlsafe(48)
_DEV_SECRET_WARNING_EMITTED = False
_ALGORITHM = "HS256"


def _get_signing_secret() -> str:
    global _DEV_SECRET_WARNING_EMITTED

    configured = (settings.AUTH_JWT_SECRET or "").strip()
    if configured:
        return configured

    environment = str(settings.ENVIRONMENT).strip().lower()
    if environment in {"production", "staging", "homologation"}:
        raise RuntimeError("AUTH_JWT_SECRET is required in deployed environments")

    if not _DEV_SECRET_WARNING_EMITTED:
        logger.warning("auth_jwt_secret_missing_using_ephemeral_process_key")
        _DEV_SECRET_WARNING_EMITTED = True
    return _DEV_FALLBACK_SECRET


def _issuer() -> str:
    return str(getattr(settings, "AUTH_JWT_ISSUER", "janus-api"))


def _audience() -> str:
    return str(getattr(settings, "AUTH_JWT_AUDIENCE", "janus-clients"))


def _encode_token(
    *,
    actor_id: str | int,
    token_type: str,
    auth_method: str,
    expires_in: int,
    audience: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(actor_id),
        "amr": [str(auth_method)],
        "typ": token_type,
        "iat": now,
        "nbf": now,
        "exp": now + int(expires_in),
        "jti": uuid.uuid4().hex,
        "iss": _issuer(),
        "aud": audience or _audience(),
    }
    if extra_claims:
        payload.update(extra_claims)
    return cast(
        str,
        jwt.encode(
        payload,
        _get_signing_secret(),
        algorithm=_ALGORITHM,
        headers={"kid": str(getattr(settings, "AUTH_JWT_KEY_ID", "primary"))},
        ),
    )


def create_token(
    user_id: int,
    expires_in: int | None = None,
    *,
    auth_method: str = AuthMethod.LOCAL,
) -> str:
    return _encode_token(
        actor_id=user_id,
        token_type="access",
        auth_method=auth_method,
        expires_in=int(expires_in or settings.AUTH_JWT_EXPIRES_SECONDS),
    )


def create_refresh_token(
    user_id: int,
    expires_in: int | None = None,
    *,
    auth_method: str = AuthMethod.LOCAL,
) -> str:
    return _encode_token(
        actor_id=user_id,
        token_type="refresh",
        auth_method=auth_method,
        expires_in=int(expires_in or settings.AUTH_REFRESH_EXPIRES_SECONDS),
    )


def create_actor_envelope(actor: ActorContext, *, audience: str) -> str:
    return _encode_token(
        actor_id=actor.actor_id,
        token_type="actor-context",
        auth_method=actor.auth_method,
        expires_in=int(getattr(settings, "ACTOR_CONTEXT_ENVELOPE_TTL_SECONDS", 60)),
        audience=audience,
        extra_claims={
            "actor_type": actor.actor_type.value,
            "roles": list(actor.roles),
            "trace_id": actor.trace_id,
            "resource_owner": actor.resource_owner,
        },
    )


def _decode_token(token: str, *, token_type: str, audience: str | None = None) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            _get_signing_secret(),
            algorithms=[_ALGORITHM],
            audience=audience or _audience(),
            issuer=_issuer(),
            options={"require": ["sub", "amr", "typ", "iat", "nbf", "exp", "jti"]},
        )
        if payload.get("typ") != token_type:
            return None
        return cast(dict[str, Any], payload)
    except jwt.PyJWTError:
        return None


def verify_access_claims(token: str) -> dict[str, Any] | None:
    return _decode_token(token, token_type="access")


def verify_token(token: str) -> int | None:
    payload = verify_access_claims(token)
    if payload is None:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None


def verify_refresh_token(token: str) -> int | None:
    payload = _decode_token(token, token_type="refresh")
    if payload is None:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None


def verify_actor_envelope(token: str, *, audience: str) -> ActorContext | None:
    payload = _decode_token(token, token_type="actor-context", audience=audience)
    if payload is None:
        return None
    try:
        actor = ActorContext.authenticated(
            actor_id=payload["sub"],
            roles=payload.get("roles") or (),
            auth_method=(payload.get("amr") or [AuthMethod.INTERNAL])[0],
            trace_id=payload["trace_id"],
            actor_type=ActorType(str(payload.get("actor_type") or ActorType.SYSTEM)),
        )
        owner = payload.get("resource_owner")
        return actor.bind_resource_owner(owner) if owner is not None else actor
    except (KeyError, TypeError, ValueError):
        return None


def get_actor_context(request: Request) -> ActorContext | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    payload = verify_access_claims(auth.split(" ", 1)[1].strip())
    if payload is None:
        return None
    try:
        actor_id = int(payload["sub"])
        from app.repositories.user_repository import UserRepository

        roles = UserRepository().list_roles(actor_id)
        actor_type = ActorType.SYSTEM if "SYSTEM" in roles else ActorType.HUMAN
        trace_id = str(getattr(request.state, "trace_id", "") or uuid.uuid4().hex)
        return ActorContext.authenticated(
            actor_id=actor_id,
            roles=roles,
            auth_method=(payload.get("amr") or ["unknown"])[0],
            trace_id=trace_id,
            actor_type=actor_type,
        )
    except Exception:
        return None


def get_actor_user_id(request: Request) -> int | None:
    """Compatibility accessor backed exclusively by ActorContext."""
    actor = getattr(getattr(request, "state", None), "actor_context", None)
    try:
        if actor is not None:
            return int(actor.actor_id)
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            return verify_token(auth.split(" ", 1)[1].strip())
        return None
    except (TypeError, ValueError):
        return None
