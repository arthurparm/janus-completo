from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy (CSP)
        # Restricts the sources from which content can be loaded
        # Note: 'unsafe-inline' and 'unsafe-eval' are permitted for Swagger UI compatibility
        # In a production frontend-only scenario, these should be removed.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " 
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; " # Prevent embedding
            "object-src 'none'; "      # Prevent Flash/Java
            "base-uri 'self';"         # Prevent base tag hijacking
        )
        
        # Strict Transport Security (HSTS)
        # Enforces HTTPS connections
        # max-age=31536000 (1 year), includeSubDomains, preload
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Content-Type-Options
        # Prevents MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        # Prevents clickjacking by denying rendering in a frame
        response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer-Policy
        # Controls how much referrer information is sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Cache-Control (Secure by default for API)
        # Prevent caching of sensitive data unless overridden by specific endpoints
        if "Cache-Control" not in response.headers:
             response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
             response.headers["Pragma"] = "no-cache"
             response.headers["Expires"] = "0"

        # Permissions-Policy (formerly Feature-Policy)
        # Controls which browser features can be used
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "vr=()"
        )
        
        return response
