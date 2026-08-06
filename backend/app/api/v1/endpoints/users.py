from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.security.request_guard import (
    require_service_actor,
)
from app.models.consent_scopes import is_valid_scope
from app.repositories.user_repository import ConsentRepository, UserRepository

router = APIRouter(
    tags=["Users"],
    prefix="/users",
    dependencies=[Depends(require_service_actor)],
)
user_router = APIRouter(tags=["Users"], prefix="/users")


class CreateUserRequest(BaseModel):
    email: str | None = Field(None)
    display_name: str | None = Field(None)


class UserResponse(BaseModel):
    id: int
    email: str | None
    display_name: str | None
    status: str | None
    roles: list[str] = Field(default_factory=list)


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(None, max_length=100)


def get_user_repo(request: Request) -> UserRepository:
    return UserRepository()


@user_router.get("/me", response_model=UserResponse, operation_id="get_current_user")
async def get_current_user(request: Request, repo: UserRepository = Depends(get_user_repo)):
    from app.core.security.request_guard import require_authenticated_actor_id

    user = repo.get_user(int(require_authenticated_actor_id(request)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        roles=list(getattr(request.state.actor_context, "roles", ())),
    )


@user_router.patch("/me", response_model=UserResponse, operation_id="update_current_user")
async def update_current_user(
    payload: UpdateMeRequest,
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
):
    from app.core.security.request_guard import require_authenticated_actor_id

    user = repo.update_display_name(
        int(require_authenticated_actor_id(request)), payload.display_name
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        roles=list(getattr(request.state.actor_context, "roles", ())),
    )


@router.post("/", response_model=UserResponse)
async def create_user(payload: CreateUserRequest, repo: UserRepository = Depends(get_user_repo)):
    u = repo.create_user(email=payload.email, display_name=payload.display_name)
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)


@router.get("/{target_actor_id:int}", response_model=UserResponse)
async def get_user(
    target_actor_id: int,
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
):
    require_service_actor(request)
    u = repo.get_user(target_actor_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)


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


@router.post("/{target_actor_id:int}/consents", response_model=ConsentResponse)
async def add_consent(
    target_actor_id: int,
    payload: ConsentRequest,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_service_actor(request)
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


@router.get("/{target_actor_id:int}/consents")
async def list_consents(
    target_actor_id: int,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_service_actor(request)
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


@router.delete("/{target_actor_id:int}/consents/{scope}")
async def revoke_consent(
    target_actor_id: int,
    scope: str,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
):
    require_service_actor(request)
    if not is_valid_scope(scope):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")
    ok = repo.revoke_consent(user_id=target_actor_id, scope=scope)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return {"status": "revoked", "scope": scope}
