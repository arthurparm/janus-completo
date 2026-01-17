from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.infrastructure.auth import create_token
from app.core.infrastructure.firebase import get_firebase_service
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


class FirebaseExchangeRequest(BaseModel):
    token: str = Field(..., min_length=10)


class AuthUserResponse(BaseModel):
    id: str
    roles: list[str]
    permissions: list[str]


class AuthExchangeResponse(BaseModel):
    token: str
    user: AuthUserResponse


def _ensure_firebase_initialized() -> None:
    import firebase_admin

    if firebase_admin._apps:
        return
    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
    if not cred_path:
        raise RuntimeError("Firebase credentials missing")
    db_url = getattr(settings, "FIREBASE_DATABASE_URL", None)
    get_firebase_service().initialize(cred_path, db_url)


@router.post("/firebase/exchange", response_model=AuthExchangeResponse)
async def firebase_exchange(
    payload: FirebaseExchangeRequest, repo: UserRepository = Depends(get_user_repo)
):
    if not getattr(settings, "FIREBASE_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firebase auth disabled"
        )

    try:
        _ensure_firebase_initialized()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase not configured",
        )

    try:
        from firebase_admin import auth as firebase_auth

        decoded = firebase_auth.verify_id_token(payload.token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = str(decoded.get("uid") or decoded.get("sub") or "").strip()
    email = str(decoded.get("email") or "").strip()
    display_name = str(decoded.get("name") or email or "").strip() or None
    if not uid and not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="uid/email missing"
        )

    user = repo.get_by_external_id(uid) if uid else None
    if not user and email:
        user = repo.get_by_email(email)

    if not user:
        user = repo.create_user(email=email or None, display_name=display_name, external_id=uid or None)
    elif uid and not user.external_id:
        repo.set_external_id(int(user.id), uid)

    if not repo.has_any_admin() and not repo.has_role(int(user.id), "ADMIN"):
        repo.assign_role(int(user.id), "ADMIN")

    roles = [r.lower() for r in repo.list_roles(int(user.id)) if isinstance(r, str)]
    if repo.is_admin(int(user.id)) and "admin" not in roles:
        roles.append("admin")

    permissions = ["read"]
    tok = create_token(int(user.id), 3600)
    return AuthExchangeResponse(
        token=tok,
        user=AuthUserResponse(id=str(user.id), roles=roles, permissions=permissions),
    )
