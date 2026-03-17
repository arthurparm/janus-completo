from __future__ import annotations

from fastapi import Request

from app.config import settings
from app.core.infrastructure.auth import get_actor_user_id
from app.repositories.user_repository import UserRepository


def _normalize_identifier(value: str | int | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _chat_unlimited_allowlist() -> set[str]:
    raw = getattr(settings, "CHAT_UNLIMITED_USERS", []) or []
    return {_normalize_identifier(item) for item in raw if _normalize_identifier(item)}


def is_chat_unlimited_user(user_id: str | int | None) -> bool:
    normalized = _normalize_identifier(user_id)
    if not normalized or normalized.startswith("anon:"):
        return False

    allowlist = _chat_unlimited_allowlist()
    if normalized in allowlist:
        return True

    try:
        user_repo = UserRepository()
        numeric_user_id = int(str(user_id).strip())
    except Exception:
        return False

    try:
        if user_repo.is_admin(numeric_user_id):
            return True
    except Exception:
        pass

    try:
        user = user_repo.get_user(numeric_user_id)
        email = _normalize_identifier(getattr(user, "email", None))
        if email and email in allowlist:
            return True
    except Exception:
        return False

    return False


def is_chat_unlimited_request(request: Request | None) -> bool:
    if request is None:
        return False
    try:
        actor_user_id = get_actor_user_id(request)
    except Exception:
        return False
    return is_chat_unlimited_user(actor_user_id)
