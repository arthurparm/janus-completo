from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.security.request_guard import (
    require_admin_actor,
)
from app.models.consent_scopes import is_valid_scope
from app.repositories.user_repository import ConsentRepository, UserRepository

router = APIRouter(
    tags=["Users"],
    prefix="/users",
    dependencies=[Depends(require_admin_actor)],
)


class CreateUserRequest(BaseModel):
    email: str | None = Field(None)
    display_name: str | None = Field(None)


class UserResponse(BaseModel):
    id: int
    email: str | None
    display_name: str | None
    status: str | None


class AssignRoleRequest(BaseModel):
    role_name: str = Field(..., min_length=2)


def get_user_repo(request: Request) -> UserRepository:
    return UserRepository()


@router.post("/", response_model=UserResponse)
async def create_user(payload: CreateUserRequest, repo: UserRepository = Depends(get_user_repo)):
    u = repo.create_user(email=payload.email, display_name=payload.display_name)
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)


@router.get("/{target_actor_id}", response_model=UserResponse)
async def get_user(
    target_actor_id: int,
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
):
    require_admin_actor(request)
    u = repo.get_user(target_actor_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)


@router.post("/{target_actor_id}/roles")
async def assign_role(
    target_actor_id: int,
    payload: AssignRoleRequest,
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
):
    require_admin_actor(request)
    if payload.role_name.strip().upper() == str(getattr(settings, "SYSTEM_USER_ROLE", "SYSTEM")).upper():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SYSTEM role is reserved")
    ok = repo.assign_role(target_actor_id, payload.role_name)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign role"
        )
    return {"status": "ok"}


class ConsentRequest(BaseModel):
    scope: str = Field(..., min_length=2)
    granted: bool = True
    expires_at: str | None = None


class ConsentResponse(BaseModel):
    scope: str
    granted: bool
    created_at: str | None
    expires_at: str | None


def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()


@router.post("/{target_actor_id}/consents", response_model=ConsentResponse)
async def add_consent(
    target_actor_id: int,
    payload: ConsentRequest,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_admin_actor(request)
    if not is_valid_scope(payload.scope):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")
    from datetime import datetime

    expires = None
    try:
        expires = datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
    except Exception:
        expires = None
    c = repo.add_consent(
        user_id=target_actor_id,
        scope=payload.scope,
        granted=payload.granted,
        expires_at=expires,
    )
    return ConsentResponse(
        scope=c.scope,
        granted=c.granted,
        created_at=str(c.created_at),
        expires_at=str(c.expires_at) if c.expires_at else None,
    )


@router.get("/{target_actor_id}/consents")
async def list_consents(
    target_actor_id: int,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_admin_actor(request)
    items = repo.list_consents(user_id=target_actor_id)
    return [
        {
            "scope": c.scope,
            "granted": c.granted,
            "created_at": str(c.created_at),
            "expires_at": str(c.expires_at) if c.expires_at else None,
        }
        for c in items
    ]


@router.delete("/{target_actor_id}/consents/{scope}")
async def revoke_consent(
    target_actor_id: int,
    scope: str,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_admin_actor(request)
    if not is_valid_scope(scope):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")
    ok = repo.revoke_consent(user_id=target_actor_id, scope=scope)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return {"status": "revoked", "scope": scope}
