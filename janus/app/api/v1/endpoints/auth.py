from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from app.core.infrastructure.auth import create_token
from app.repositories.user_repository import UserRepository

router = APIRouter(tags=["Auth"], prefix="/auth")

class TokenRequest(BaseModel):
    user_id: int = Field(...)
    expires_in: int = Field(default=3600)

class TokenResponse(BaseModel):
    token: str

def get_user_repo(request: Request) -> UserRepository:
    return UserRepository()

@router.post("/token", response_model=TokenResponse)
async def issue_token(payload: TokenRequest, request: Request, repo: UserRepository = Depends(get_user_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    if not actor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    actor_id = int(actor)
    target_id = int(payload.user_id)
    if actor_id != target_id and not repo.is_admin(actor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    tok = create_token(target_id, payload.expires_in)
    return TokenResponse(token=tok)