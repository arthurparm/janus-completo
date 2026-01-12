import asyncio
import time
from pathlib import Path

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.core.infrastructure.redis_manager import redis_manager

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
        # Convert requests/min to requests/sec for token bucket
        self.rate_ip = max(0.1, getattr(settings, "RATE_LIMIT_PER_IP_PER_MIN", 60) / 60.0)
        self.burst_ip = max(1, int(getattr(settings, "RATE_LIMIT_PER_IP_PER_MIN", 60)))
        
        self.rate_key = max(0.1, getattr(settings, "RATE_LIMIT_PER_KEY_PER_MIN", 300) / 60.0)
        self.burst_key = max(1, int(getattr(settings, "RATE_LIMIT_PER_KEY_PER_MIN", 300)))
        
        self.script_sha: str | None = None
        
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

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        # Health check bypass
        path = request.url.path
        if path.startswith("/metrics") or path in ("/healthz", "/livez", "/readyz"):
            return await call_next(request)

        # Fail open if Redis is down
        if not getattr(settings, "REDIS_ENABLED", False):
            # Fallback to allow if Redis is disabled but Rate Limit is enabled logic? 
            # Ideally we should warn, but here we just proceed to avoid blocking.
            return await call_next(request)

        try:
            client = redis_manager.client
            script_sha = await self._get_script_sha()
            if not script_sha:
                # If script loading fails, fail open
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
                    return await call_next(request) # Fail open

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

        except Exception as e:
            # Redis failure -> Fail Open
            # logger.warning(f"Rate limiting failed: {e}")
            return await call_next(request)

