from fastapi import APIRouter, Depends, HTTPException, Request, status
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
async def issue_token(
    payload: TokenRequest, request: Request, repo: UserRepository = Depends(get_user_repo)
):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    if not actor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    actor_id = int(actor)
    target_id = int(payload.user_id)
    if actor_id != target_id and not repo.is_admin(actor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    tok = create_token(target_id, payload.expires_in)
    return TokenResponse(token=tok)


class SupabaseExchangeRequest(BaseModel):
    token: str = Field(...)


@router.post("/supabase/exchange", response_model=TokenResponse)
async def supabase_exchange(
    payload: SupabaseExchangeRequest, repo: UserRepository = Depends(get_user_repo)
):
    try:
        parts = payload.token.split(".")
        if len(parts) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
        import base64
        import json

        body = parts[1]
        body_padded = body + "=" * (-len(body) % 4)
        data = json.loads(base64.urlsafe_b64decode(body_padded.encode("ascii")).decode("utf-8"))
        email = str(data.get("email") or "").strip()
        sub = str(data.get("sub") or "").strip()
        if not email and not sub:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email/sub missing"
            )
        u = repo.get_by_email(email) if email else None
        if not u:
            display = (data.get("user_metadata") or {}).get("full_name") or None
            u = repo.create_user(email=email or None, display_name=display)
        tok = create_token(int(u.id), 3600)
        return TokenResponse(token=tok)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
