import asyncio
import hashlib
import os
from collections import defaultdict

from fastapi import HTTPException, Request, status

_SSE_SLOT_LOCK = asyncio.Lock()
_SSE_SLOTS_BY_USER: dict[str, int] = defaultdict(int)
_SSE_SLOTS_TOTAL = 0


def actor_user_id(http: Request | None) -> str | None:
    if http is None:
        return None
    try:
        actor = getattr(http.state, "actor_user_id", None)
        return str(actor) if actor else None
    except Exception:
        return None


def actor_project_id(http: Request | None) -> str | None:
    if http is None:
        return None
    try:
        project = getattr(http.state, "actor_project_id", None)
        return str(project) if project else None
    except Exception:
        return None


def anonymous_user_id(http: Request | None) -> str | None:
    if http is None:
        return None
    try:
        client_ip = (
            (http.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            or (http.client.host if http.client else "")
        )
        user_agent = http.headers.get("user-agent") or "unknown"
        if not client_ip:
            return None
        digest = hashlib.sha256(f"{client_ip}|{user_agent}".encode("utf-8")).hexdigest()[:16]
        return f"anon:{digest}"
    except Exception:
        return None


def resolve_user_id(http: Request | None, explicit_user_id: str | None) -> str | None:
    return explicit_user_id or actor_user_id(http) or anonymous_user_id(http)


async def acquire_sse_slot(user_id: str | None) -> str:
    max_per_user = max(1, int(os.getenv("CHAT_SSE_MAX_CONNECTIONS_PER_USER", "4")))
    max_global = max(1, int(os.getenv("CHAT_SSE_MAX_GLOBAL_CONNECTIONS", "250")))
    slot_user = str(user_id or "anonymous")

    global _SSE_SLOTS_TOTAL
    async with _SSE_SLOT_LOCK:
        if _SSE_SLOTS_TOTAL >= max_global:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="SSE capacity exceeded (global).",
            )
        current_user_slots = int(_SSE_SLOTS_BY_USER.get(slot_user, 0))
        if current_user_slots >= max_per_user:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="SSE capacity exceeded for this user.",
            )
        _SSE_SLOTS_BY_USER[slot_user] = current_user_slots + 1
        _SSE_SLOTS_TOTAL += 1
    return slot_user


async def release_sse_slot(slot_user: str) -> None:
    global _SSE_SLOTS_TOTAL
    async with _SSE_SLOT_LOCK:
        current = int(_SSE_SLOTS_BY_USER.get(slot_user, 0))
        if current <= 1:
            _SSE_SLOTS_BY_USER.pop(slot_user, None)
        else:
            _SSE_SLOTS_BY_USER[slot_user] = current - 1
        _SSE_SLOTS_TOTAL = max(0, _SSE_SLOTS_TOTAL - 1)


def ensure_origin_allowed(http: Request | None) -> None:
    if http is None:
        return
    try:
        from app.config import settings
    except Exception:
        settings = None

    origin = (http.headers.get("origin") or "").lower()
    try:
        allowed_origins = list(getattr(settings, "CORS_ALLOW_ORIGINS", [])) or []
    except Exception:
        allowed_origins = []
    normalized_allowed = [o.lower() for o in allowed_origins if isinstance(o, str)]

    if not origin:
        return
    if "*" in normalized_allowed:
        return
    if not normalized_allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    if origin not in normalized_allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
