from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.repositories.user_repository import UserRepository


def get_request_actor_id(request: Request | None) -> int | None:
    if request is None:
        return None
    actor = getattr(request.state, "actor_user_id", None)
    if actor is None:
        return None
    try:
        return int(actor)
    except Exception:
        return None


def require_authenticated_actor_id(request: Request) -> int:
    actor_id = get_request_actor_id(request)
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return actor_id


def require_admin_actor(request: Request) -> int:
    actor_id = require_authenticated_actor_id(request)
    if not UserRepository().is_admin(actor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return actor_id


def require_same_user_or_admin(request: Request, target_user_id: int) -> int:
    actor_id = require_authenticated_actor_id(request)
    if actor_id != int(target_user_id) and not UserRepository().is_admin(actor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return actor_id


def resolve_user_scope_id(request: Request | None, explicit_user_id: str | None) -> str | None:
    if explicit_user_id:
        return str(explicit_user_id)
    actor_id = get_request_actor_id(request)
    return str(actor_id) if actor_id is not None else None
