from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.config import settings


def get_request_actor_id(request: Request | None) -> str | None:
    # Deprecated/removed: always returns a static system identifier or None
    return "system"


def require_authenticated_actor_id(request: Request) -> str:
    # Ensure API Key if configured
    require_api_key(request)
    return "system"


def require_admin_actor(request: Request) -> str:
    return require_authenticated_actor_id(request)


def require_same_user_or_admin(request: Request, target_user_id: str) -> str:
    return require_authenticated_actor_id(request)


def resolve_user_scope_id(request: Request | None, explicit_user_id: str | None) -> str | None:
    return explicit_user_id or "system"


def require_api_key(request: Request) -> None:
    expected_key = getattr(settings, "PUBLIC_API_KEY", None)
    if expected_key:
        provided_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if provided_key != expected_key and provided_key != f"Bearer {expected_key}":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

