import asyncio
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request, status

from app.core.security.chat_unlimited import is_chat_unlimited_user

_SSE_SLOT_LOCK = asyncio.Lock()
_SSE_SLOTS_BY_USER_CHANNEL: dict[tuple[str, str], int] = defaultdict(int)
_SSE_SLOTS_TOTAL = 0
SSEChannel = Literal["chat_stream", "agent_events"]


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


def is_chat_auth_enforced() -> bool:
    return True


def _auth_header_present(http: Request | None) -> bool:
    try:
        return bool((http.headers.get("authorization") or "").strip()) if http else False
    except Exception:
        return False


def _chat_http_error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "message": detail,
            "code": code,
        },
    )


@dataclass
class ChatIdentityResolution:
    user_id: str | None
    identity_source: str
    auth_present: bool
    authenticated: bool


def resolve_authenticated_user_context(
    http: Request | None,
    explicit_user_id: str | None,
    *,
    allow_anonymous_fallback: bool = False,
    endpoint_label: str = "/api/v1/chat",
) -> ChatIdentityResolution:
    """Resolve chat identity from an authenticated bearer-derived actor only."""
    del explicit_user_id
    del allow_anonymous_fallback
    del endpoint_label

    auth_present = _auth_header_present(http)
    actor = actor_user_id(http)

    if actor and auth_present:
        return ChatIdentityResolution(
            user_id=actor,
            identity_source="actor",
            auth_present=True,
            authenticated=True,
        )
    return ChatIdentityResolution(
        user_id=None,
        identity_source="unknown",
        auth_present=auth_present,
        authenticated=False,
    )


def require_actor_user_id(http: Request | None) -> str:
    """Strict helper: always require authenticated actor when enforcement is enabled.

    In transition mode, preserves compatibility by delegating to resolution without anonymous fallback.
    """
    ctx = resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat",
    )
    if ctx.user_id:
        return ctx.user_id
    raise _chat_http_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        code="CHAT_AUTH_REQUIRED",
    )


def resolve_authenticated_user_id(http: Request | None, explicit_user_id: str | None) -> str:
    """Resolve user id for chat endpoints, enforcing auth when configured.

    In transition mode, may return explicit/header-based identity and optionally anonymous (if caller uses
    `resolve_authenticated_user_context(..., allow_anonymous_fallback=True)` instead).
    """
    ctx = resolve_authenticated_user_context(
        http,
        explicit_user_id,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat",
    )
    if ctx.user_id:
        return ctx.user_id
    raise _chat_http_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        code="CHAT_AUTH_REQUIRED",
    )


def _channel_limit(channel: SSEChannel) -> int:
    legacy_limit = os.getenv("CHAT_SSE_MAX_CONNECTIONS_PER_USER", "4")
    if channel == "chat_stream":
        return max(1, int(os.getenv("CHAT_SSE_MAX_CHAT_STREAMS_PER_USER", legacy_limit)))
    return max(1, int(os.getenv("CHAT_SSE_MAX_AGENT_EVENT_STREAMS_PER_USER", legacy_limit)))


async def acquire_sse_slot(*, channel: SSEChannel, user_id: str) -> str:
    max_per_user_channel = _channel_limit(channel)
    max_global = max(1, int(os.getenv("CHAT_SSE_MAX_GLOBAL_CONNECTIONS", "250")))
    slot_user = str(user_id).strip()
    if is_chat_unlimited_user(slot_user):
        return f"unlimited:{slot_user}"

    global _SSE_SLOTS_TOTAL
    async with _SSE_SLOT_LOCK:
        if _SSE_SLOTS_TOTAL >= max_global:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="SSE capacity exceeded (global).",
            )
        slot_key = (slot_user, channel)
        current_channel_slots = int(_SSE_SLOTS_BY_USER_CHANNEL.get(slot_key, 0))
        if current_channel_slots >= max_per_user_channel:
            try:
                import structlog

                structlog.get_logger(__name__).warning(
                    "chat_sse_capacity_exceeded_per_user_channel",
                    channel=channel,
                    limit=max_per_user_channel,
                    current_slots=current_channel_slots,
                    total_slots=_SSE_SLOTS_TOTAL,
                    global_limit=max_global,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="SSE capacity exceeded for this user.",
            )
        _SSE_SLOTS_BY_USER_CHANNEL[slot_key] = current_channel_slots + 1
        _SSE_SLOTS_TOTAL += 1
    return slot_user


async def release_sse_slot(slot_user: str, *, channel: SSEChannel) -> None:
    if str(slot_user).startswith("unlimited:"):
        return
    global _SSE_SLOTS_TOTAL
    async with _SSE_SLOT_LOCK:
        slot_key = (slot_user, channel)
        current = int(_SSE_SLOTS_BY_USER_CHANNEL.get(slot_key, 0))
        if current <= 1:
            _SSE_SLOTS_BY_USER_CHANNEL.pop(slot_key, None)
        else:
            _SSE_SLOTS_BY_USER_CHANNEL[slot_key] = current - 1
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
