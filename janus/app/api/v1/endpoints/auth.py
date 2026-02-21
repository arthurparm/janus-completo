from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.infrastructure.auth import create_token
from app.core.security.passwords import hash_password, verify_password
from app.repositories.user_repository import ConsentRepository, UserRepository

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


class LocalRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2)
    cpf: str | None = None
    phone: str | None = None
    terms: bool = Field(default=False)


class LocalLoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    # Login accepts legacy short passwords; strength is enforced on register/reset.
    password: str = Field(..., min_length=1)


class LocalResetRequest(BaseModel):
    email: str = Field(..., min_length=3)


class LocalResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)


class LocalAuthUserResponse(BaseModel):
    id: str
    email: str | None = None
    username: str | None = None
    display_name: str | None = None
    roles: list[str]
    permissions: list[str]


class LocalAuthResponse(BaseModel):
    token: str
    user: LocalAuthUserResponse


class LocalResetResponse(BaseModel):
    status: str
    reset_token: str | None = None


def _can_return_reset_token() -> bool:
    if str(getattr(settings, "ENVIRONMENT", "")).lower() == "production":
        return False
    return bool(getattr(settings, "AUTH_RESET_RETURN_TOKEN", False))


def _ensure_firebase_initialized() -> None:
    import firebase_admin
    from app.core.infrastructure.firebase import get_firebase_service

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


@router.post("/local/register", response_model=LocalAuthResponse)
async def local_register(
    payload: LocalRegisterRequest, repo: UserRepository = Depends(get_user_repo)
):
    if not payload.terms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Terms not accepted"
        )

    email = payload.email.strip().lower()
    username = payload.username.strip()
    full_name = payload.full_name.strip()

    if repo.get_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if repo.get_by_username(username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    pw_hash = hash_password(payload.password)
    user = repo.create_user(
        email=email,
        display_name=full_name,
        username=username,
        password_hash=pw_hash,
    )

    if not repo.has_any_admin():
        if not repo.has_role(int(user.id), "ADMIN"):
            repo.assign_role(int(user.id), "ADMIN")
    else:
        if not repo.has_role(int(user.id), "USER"):
            repo.assign_role(int(user.id), "USER")

    try:
        ConsentRepository().add_consent(int(user.id), scope="terms_v1", granted=True)
    except Exception:
        pass

    tok = create_token(int(user.id), 3600)
    return LocalAuthResponse(token=tok, user=_build_local_user(repo, user))


@router.post("/local/login", response_model=LocalAuthResponse)
async def local_login(payload: LocalLoginRequest, repo: UserRepository = Depends(get_user_repo)):
    identifier = (payload.email or "").strip().lower()
    username = (payload.username or "").strip()

    user = None
    if identifier:
        user = repo.get_by_email(identifier)
    if user is None and username:
        user = repo.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    tok = create_token(int(user.id), 3600)
    return LocalAuthResponse(token=tok, user=_build_local_user(repo, user))


@router.get("/local/me", response_model=LocalAuthUserResponse)
async def local_me(request: Request, repo: UserRepository = Depends(get_user_repo)):
    uid = getattr(request.state, "actor_user_id", None)
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    user = repo.get_user(int(uid))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _build_local_user(repo, user)


@router.post("/local/request-reset", response_model=LocalResetResponse)
async def local_request_reset(
    payload: LocalResetRequest, repo: UserRepository = Depends(get_user_repo)
):
    email = payload.email.strip().lower()
    user = repo.get_by_email(email)
    if not user:
        return LocalResetResponse(status="ok", reset_token=None)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    ttl_seconds = max(300, int(getattr(settings, "AUTH_RESET_TOKEN_TTL_SECONDS", 3600)))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    repo.set_reset_token(int(user.id), token_hash, expires_at=expires_at)

    if _can_return_reset_token():
        return LocalResetResponse(status="ok", reset_token=token)
    return LocalResetResponse(status="ok", reset_token=None)


@router.post("/local/reset", response_model=LocalResetResponse)
async def local_reset_password(
    payload: LocalResetConfirmRequest, repo: UserRepository = Depends(get_user_repo)
):
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    user = repo.get_by_reset_token(token_hash)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    pw_hash = hash_password(payload.password)
    repo.set_password_hash(int(user.id), pw_hash)
    repo.set_reset_token(int(user.id), None, expires_at=None)
    return LocalResetResponse(status="ok", reset_token=None)


def _build_local_user(repo: UserRepository, user) -> LocalAuthUserResponse:
    roles = [r.lower() for r in repo.list_roles(int(user.id)) if isinstance(r, str)]
    if repo.is_admin(int(user.id)) and "admin" not in roles:
        roles.append("admin")
    if not roles:
        roles = ["user"]
    permissions = ["read"]
    return LocalAuthUserResponse(
        id=str(user.id),
        email=user.email,
        username=getattr(user, "username", None),
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )
