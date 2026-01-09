import asyncio
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class _TokenBucket:
    def __init__(self, rate_per_minute: int, burst: int | None = None):
        self.capacity = max(1, burst or rate_per_minute)
        self.tokens = self.capacity
        self.rate_per_sec = rate_per_minute / 60.0
        self.timestamp = time.time()
        self._lock = asyncio.Lock()

    async def allow(self) -> bool:
        async with self._lock:
            now = time.time()
            delta = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + delta * self.rate_per_sec)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory token bucket por IP e por API Key (X-API-Key)."""

    def __init__(self, app):
        super().__init__(app)
        self.enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self.ip_limit = max(1, getattr(settings, "RATE_LIMIT_PER_IP_PER_MIN", 60))
        self.key_limit = max(1, getattr(settings, "RATE_LIMIT_PER_KEY_PER_MIN", 300))
        self._buckets_ip: dict[str, _TokenBucket] = {}
        self._buckets_key: dict[str, _TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def _get_bucket(
        self, store: dict[str, _TokenBucket], key: str, rate: int
    ) -> _TokenBucket:
        b = store.get(key)
        if b is not None:
            return b
        async with self._lock:
            b = store.get(key)
            if b is None:
                b = _TokenBucket(rate)
                store[key] = b
            return b

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        # is metrics/health exempt
        path = request.url.path
        if path.startswith("/metrics") or path in ("/healthz", "/livez", "/readyz"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key")

        # per-IP check
        ip_bucket = await self._get_bucket(self._buckets_ip, client_ip, self.ip_limit)
        if not await ip_bucket.allow():
            return Response(
                content='{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Rate limit exceeded (per IP)","instance":"%s"}'
                % path,
                media_type="application/problem+json",
                status_code=429,
                headers={"Retry-After": "60"},
            )

        # per-key check if header present
        if api_key:
            key_bucket = await self._get_bucket(self._buckets_key, api_key, self.key_limit)
            if not await key_bucket.allow():
                return Response(
                    content='{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Rate limit exceeded (per API key)","instance":"%s"}'
                    % path,
                    media_type="application/problem+json",
                    status_code=429,
                    headers={"Retry-After": "60"},
                )

        return await call_next(request)
