"""HTTP middleware to capture domain-level SLO metrics (OQ-002)."""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.monitoring.domain_slo_metrics import (
    DOMAIN_REQUEST_LATENCY_SECONDS,
    DOMAIN_REQUESTS_TOTAL,
    derive_domain_from_path,
    is_http_error,
)


class DomainSLOMetricsMiddleware(BaseHTTPMiddleware):
    """Collect request count/latency by domain for chat/rag/tools/workers."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        domain = derive_domain_from_path(path)
        should_track = domain != "other"
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            if should_track:
                elapsed = max(0.0, time.perf_counter() - started)
                DOMAIN_REQUESTS_TOTAL.labels(domain=domain, outcome="error").inc()
                DOMAIN_REQUEST_LATENCY_SECONDS.labels(domain=domain).observe(elapsed)
            raise

        if should_track:
            elapsed = max(0.0, time.perf_counter() - started)
            outcome = "error" if is_http_error(getattr(response, "status_code", None)) else "success"
            DOMAIN_REQUESTS_TOTAL.labels(domain=domain, outcome=outcome).inc()
            DOMAIN_REQUEST_LATENCY_SECONDS.labels(domain=domain).observe(elapsed)
        return response

