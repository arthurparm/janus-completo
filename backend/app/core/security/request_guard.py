from __future__ import annotations

from app.config import settings
from fastapi import HTTPException, Request, status


def get_request_actor_id(request: Request | None) -> str | None:
    if request is None:
        return None
    try:
        actor = getattr(request.state, "actor_user_id", None)
        return str(actor) if actor else None
    except Exception:
        return None


def require_authenticated_actor_id(request: Request) -> str:
    actor = get_request_actor_id(request)
    require_api_key(request)
    if actor:
        return actor
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_admin_actor(request: Request) -> str:
    return require_authenticated_actor_id(request)


def require_same_user_or_admin(request: Request, target_user_id: str) -> str:
    return require_authenticated_actor_id(request)


def resolve_user_scope_id(request: Request | None, explicit_user_id: str | None) -> str | None:
    if explicit_user_id:
        return str(explicit_user_id)
    return get_request_actor_id(request)


def require_api_key(request: Request) -> None:
    expected_key = getattr(settings, "PUBLIC_API_KEY", None)
    if expected_key:
        provided_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if provided_key != expected_key and provided_key != f"Bearer {expected_key}":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

