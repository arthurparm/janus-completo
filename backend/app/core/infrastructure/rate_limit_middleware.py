import asyncio
import time
from pathlib import Path
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.core.infrastructure.redis_manager import redis_manager
from app.core.security.chat_unlimited import is_chat_unlimited_request

try:
    from prometheus_client import Counter
except Exception:

    class _NoopCounter:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    Counter = _NoopCounter  # type: ignore[assignment]

_RATE_LIMIT_FALLBACK_TOTAL = Counter(
    "rate_limit_fallback_total",
    "Fallbacks locais do rate limiter",
    ["path", "status"],
)

# Load Lua script on startup
LUA_SCRIPT_PATH = Path(__file__).parent / "lua" / "token_bucket.lua"
try:
    with open(LUA_SCRIPT_PATH, "r", encoding="utf-8") as f:
        TOKEN_BUCKET_SCRIPT_CONTENT = f.read()
except Exception:
    TOKEN_BUCKET_SCRIPT_CONTENT = ""


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        env = str(getattr(settings, "ENVIRONMENT", "development")).strip().lower()
        self.fail_closed = bool(getattr(settings, "RATE_LIMIT_FAIL_CLOSED", False)) or env == "production"
        # Convert requests/min to requests/sec for token bucket
        self.rate_ip = max(0.1, getattr(settings, "RATE_LIMIT_PER_IP_PER_MIN", 60) / 60.0)
        self.burst_ip = max(1, int(getattr(settings, "RATE_LIMIT_PER_IP_PER_MIN", 60)))
        
        self.rate_key = max(0.1, getattr(settings, "RATE_LIMIT_PER_KEY_PER_MIN", 300) / 60.0)
        self.burst_key = max(1, int(getattr(settings, "RATE_LIMIT_PER_KEY_PER_MIN", 300)))
        
        self.script_sha: str | None = None
        self._fallback_lock = Lock()
        self._fallback_buckets: dict[str, tuple[float, float]] = {}

    def _service_unavailable_response(self, path: str) -> Response:
        return Response(
            content='{"type":"about:blank","title":"Service Unavailable","status":503,"detail":"Rate limiter unavailable","instance":"%s"}'
            % path,
            media_type="application/problem+json",
            status_code=503,
        )
        
    async def _get_script_sha(self):
        if self.script_sha:
            return self.script_sha
        if not TOKEN_BUCKET_SCRIPT_CONTENT:
            return None
        try:
            client = redis_manager.client
            self.script_sha = await client.script_load(TOKEN_BUCKET_SCRIPT_CONTENT)
            return self.script_sha
        except Exception:
            return None

    def _should_use_local_fallback(self, path: str) -> bool:
        return path.startswith("/api/v1/documents/upload") or path.startswith(
            "/api/v1/documents/status/"
        ) or path.startswith("/api/v1/documents/list")

    def _consume_local_bucket(self, key: str) -> tuple[bool, float]:
        now = time.time()
        with self._fallback_lock:
            tokens, updated_at = self._fallback_buckets.get(key, (float(self.burst_ip), now))
            elapsed = max(0.0, now - updated_at)
            replenished = min(float(self.burst_ip), float(tokens) + (elapsed * float(self.rate_ip)))
            if replenished >= 1.0:
                self._fallback_buckets[key] = (replenished - 1.0, now)
                return True, 0.0
            self._fallback_buckets[key] = (replenished, now)
            wait_seconds = (1.0 - replenished) / max(float(self.rate_ip), 0.1)
            return False, wait_seconds

    async def _call_with_local_fallback(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = self._consume_local_bucket(f"local_rate_limit:{client_ip}:{path}")
        if not allowed:
            _RATE_LIMIT_FALLBACK_TOTAL.labels(path=path, status="blocked").inc()
            return Response(
                content='{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Rate limit exceeded (local fallback)","instance":"%s"}'
                % path,
                media_type="application/problem+json",
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        _RATE_LIMIT_FALLBACK_TOTAL.labels(path=path, status="allowed").inc()
        return await call_next(request)

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        # Health check bypass
        path = request.url.path
        if path.startswith("/metrics") or path in ("/healthz", "/livez", "/readyz"):
            return await call_next(request)
        if path.startswith("/api/v1/chat") and is_chat_unlimited_request(request):
            return await call_next(request)

        # Redis unavailable handling
        if not getattr(settings, "REDIS_ENABLED", False):
            if self.fail_closed and self._should_use_local_fallback(path):
                return await self._call_with_local_fallback(request, call_next)
            if self.fail_closed:
                return self._service_unavailable_response(path)
            return await call_next(request)

        try:
            client = redis_manager.client
            script_sha = await self._get_script_sha()
            if not script_sha:
                if self.fail_closed and self._should_use_local_fallback(path):
                    return await self._call_with_local_fallback(request, call_next)
                if self.fail_closed:
                    return self._service_unavailable_response(path)
                return await call_next(request)
            
            # Identify client
            client_ip = request.client.host if request.client else "unknown"
            api_key = request.headers.get("X-API-Key")
            
            now = time.time()
            
            # Check IP Limit
            # KEYS[1], ARGV[1]:rate, ARGV[2]:capacity, ARGV[3]:now, ARGV[4]:requested
            ip_key = f"rate_limit:ip:{client_ip}"
            
            # Execute Lua script
            # We use evalsha for performance
            try:
                allowed, val = await client.evalsha(
                    script_sha, 1, ip_key, self.rate_ip, self.burst_ip, now, 1
                )
            except Exception:
                # If script missing (redis restart), reload and retry once
                self.script_sha = None
                script_sha = await self._get_script_sha()
                if script_sha:
                    allowed, val = await client.evalsha(
                        script_sha, 1, ip_key, self.rate_ip, self.burst_ip, now, 1
                    )
                else:
                    if self.fail_closed and self._should_use_local_fallback(path):
                        return await self._call_with_local_fallback(request, call_next)
                    if self.fail_closed:
                        return self._service_unavailable_response(path)
                    return await call_next(request)

            if not allowed:
                retry_after = float(val)
                return Response(
                    content='{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Rate limit exceeded (per IP)","instance":"%s"}' % path,
                    media_type="application/problem+json",
                    status_code=429,
                    headers={"Retry-After": str(int(retry_after) + 1)},
                )
            
            # If API Key present, check Key Limit
            if api_key:
                key_key = f"rate_limit:apikey:{api_key}"
                allowed, val = await client.evalsha(
                    script_sha, 1, key_key, self.rate_key, self.burst_key, now, 1
                )
                if not allowed:
                    retry_after = float(val)
                    return Response(
                        content='{"type":"about:blank","title":"Too Many Requests","status":429,"detail":"Rate limit exceeded (API Key)","instance":"%s"}' % path,
                        media_type="application/problem+json",
                        status_code=429,
                        headers={"Retry-After": str(int(retry_after) + 1)},
                    )
            
            response = await call_next(request)
            # Optional: Add headers X-RateLimit-Limit / Remaining based on 'val' (tokens remaining)
            # valid for the last checked limit (Key takes precedence if present)
            # response.headers["X-RateLimit-Remaining"] = str(int(val))
            return response

        except Exception:
            if self.fail_closed and self._should_use_local_fallback(path):
                return await self._call_with_local_fallback(request, call_next)
            if self.fail_closed:
                return self._service_unavailable_response(path)
            return await call_next(request)
