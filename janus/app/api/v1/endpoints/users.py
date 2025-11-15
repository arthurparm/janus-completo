from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from app.repositories.user_repository import UserRepository, ConsentRepository
from app.models.consent_scopes import is_valid_scope

router = APIRouter(tags=["Users"], prefix="/users")

class CreateUserRequest(BaseModel):
    email: Optional[str] = Field(None)
    display_name: Optional[str] = Field(None)

class UserResponse(BaseModel):
    id: int
    email: Optional[str]
    display_name: Optional[str]
    status: Optional[str]

class AssignRoleRequest(BaseModel):
    role_name: str = Field(..., min_length=2)

def get_user_repo(request: Request) -> UserRepository:
    return UserRepository()

@router.post("/", response_model=UserResponse)
async def create_user(payload: CreateUserRequest, repo: UserRepository = Depends(get_user_repo)):
    u = repo.create_user(email=payload.email, display_name=payload.display_name)
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, repo: UserRepository = Depends(get_user_repo)):
    u = repo.get_user(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status)

@router.post("/{user_id}/roles")
async def assign_role(user_id: int, payload: AssignRoleRequest, request: Request, repo: UserRepository = Depends(get_user_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    if not actor or not repo.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    ok = repo.assign_role(user_id, payload.role_name)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign role")
    return {"status": "ok"}


class ConsentRequest(BaseModel):
    scope: str = Field(..., min_length=2)
    granted: bool = True
    expires_at: Optional[str] = None

class ConsentResponse(BaseModel):
    scope: str
    granted: bool
    created_at: Optional[str]
    expires_at: Optional[str]

def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()

@router.post("/{user_id}/consents", response_model=ConsentResponse)
async def add_consent(user_id: int, payload: ConsentRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not is_valid_scope(payload.scope):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")
    from datetime import datetime
    expires = None
    try:
        expires = datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
    except Exception:
        expires = None
    c = repo.add_consent(user_id=user_id, scope=payload.scope, granted=payload.granted, expires_at=expires)
    return ConsentResponse(scope=c.scope, granted=c.granted, created_at=str(c.created_at), expires_at=str(c.expires_at) if c.expires_at else None)

@router.get("/{user_id}/consents")
async def list_consents(user_id: int, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    items = repo.list_consents(user_id=user_id)
    return [{"scope": c.scope, "granted": c.granted, "created_at": str(c.created_at), "expires_at": str(c.expires_at) if c.expires_at else None} for c in items]

@router.delete("/{user_id}/consents/{scope}")
async def revoke_consent(user_id: int, scope: str, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not is_valid_scope(scope):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope")
    ok = repo.revoke_consent(user_id=user_id, scope=scope)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return {"status": "revoked", "scope": scope}
