from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import settings

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_WINDOWS_LOCK = threading.Lock()

_DEFAULT_AUTH_LIMITS: dict[str, dict[str, int]] = {
    "auth.token": {"max_attempts": 20, "window_seconds": 60},
    "auth.local_login": {"max_attempts": 10, "window_seconds": 60},
    "auth.local_request_reset": {"max_attempts": 5, "window_seconds": 60},
    "auth.local_reset": {"max_attempts": 10, "window_seconds": 60},
}


def reset_auth_rate_limit_store() -> None:
    with _WINDOWS_LOCK:
        _WINDOWS.clear()


def _get_remote_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


def _normalize_identifier(identifier: str | int | None) -> str:
    raw = str(identifier or "").strip().lower()
    if not raw:
        return "-"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _resolve_limit(endpoint_key: str) -> tuple[int, int]:
    cfg = getattr(settings, "AUTH_RATE_LIMITS", {}) or {}
    spec = cfg.get(endpoint_key, {}) if isinstance(cfg, dict) else {}
    default_spec = _DEFAULT_AUTH_LIMITS.get(endpoint_key, {"max_attempts": 10, "window_seconds": 60})
    max_attempts = int(spec.get("max_attempts", default_spec["max_attempts"]))
    window_seconds = int(spec.get("window_seconds", default_spec["window_seconds"]))
    return max(1, max_attempts), max(1, window_seconds)


def enforce_auth_rate_limit(
    request: Request | None, *, endpoint_key: str, identifier: str | int | None = None
) -> None:
    if not bool(getattr(settings, "AUTH_RATE_LIMIT_ENABLED", True)):
        return

    max_attempts, window_seconds = _resolve_limit(endpoint_key)
    now = time.time()
    ip = _get_remote_ip(request)
    ident = _normalize_identifier(identifier)
    key = f"{endpoint_key}:{ip}:{ident}"

    with _WINDOWS_LOCK:
        bucket = _WINDOWS[key]
        while bucket and (now - bucket[0]) >= window_seconds:
            bucket.popleft()

        if len(bucket) >= max_attempts:
            retry_after = int(max(1.0, window_seconds - (now - bucket[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
