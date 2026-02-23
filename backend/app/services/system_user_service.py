from __future__ import annotations

import structlog

from app.config import settings
from app.core.security.passwords import hash_password
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


def ensure_system_user() -> int | None:
    email = (settings.SYSTEM_USER_EMAIL or "").strip().lower()
    if not email:
        return None

    repo = UserRepository()
    user = repo.get_by_email(email)
    if user:
        role = (settings.SYSTEM_USER_ROLE or "").strip()
        if role and not repo.has_role(int(user.id), role):
            repo.assign_role(int(user.id), role)
        return int(user.id)

    password_secret = settings.SYSTEM_USER_PASSWORD
    if not password_secret:
        logger.warning("SYSTEM_USER_EMAIL configured but SYSTEM_USER_PASSWORD missing.")
        return None

    password = password_secret.get_secret_value()
    username = (settings.SYSTEM_USER_USERNAME or "").strip() or None
    if username and repo.get_by_username(username):
        logger.warning("SYSTEM_USER_USERNAME already exists; creating without username.")
        username = None

    display_name = (settings.SYSTEM_USER_DISPLAY_NAME or "").strip() or None
    pw_hash = hash_password(password)
    user = repo.create_user(
        email=email,
        display_name=display_name,
        username=username,
        password_hash=pw_hash,
    )

    role = (settings.SYSTEM_USER_ROLE or "").strip()
    if role:
        repo.assign_role(int(user.id), role)
    return int(user.id)
