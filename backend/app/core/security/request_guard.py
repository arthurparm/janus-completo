from __future__ import annotations

import hmac

from app.config import settings
from app.core.security.actor_context import ActorContext
from app.core.security.authorization import authorization_service
from fastapi import HTTPException, Request, status


def get_request_actor_context(request: Request | None) -> ActorContext | None:
    if request is None:
        return None
    return getattr(request.state, "actor_context", None)


def get_request_actor_id(request: Request | None) -> str | None:
    actor = get_request_actor_context(request)
    return actor.actor_id if actor is not None else None


def require_authenticated_actor(request: Request) -> ActorContext:
    require_api_key(request)
    return authorization_service.require_authenticated(actor=get_request_actor_context(request))


def require_authenticated_actor_id(request: Request) -> str:
    return require_authenticated_actor(request).actor_id


def require_admin_actor(request: Request) -> str:
    return require_admin_actor_context(request).actor_id


def require_admin_actor_context(request: Request) -> ActorContext:
    require_api_key(request)
    return authorization_service.require_admin(actor=get_request_actor_context(request))


def require_same_user_or_admin(request: Request, target_user_id: str | int) -> str:
    require_api_key(request)
    return authorization_service.require_owner_or_admin(
        actor=get_request_actor_context(request), resource_owner=target_user_id
    ).actor_id


def resolve_user_scope_id(request: Request | None, explicit_user_id: str | None = None) -> str | None:
    """Compatibility shim: client-provided identity is deliberately ignored."""
    _ = explicit_user_id
    return get_request_actor_id(request)


def require_api_key(request: Request) -> None:
    expected_key = str(getattr(settings, "PUBLIC_API_KEY", "") or "")
    if not expected_key:
        return
    provided_key = request.headers.get("X-API-Key") or ""
    if not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
