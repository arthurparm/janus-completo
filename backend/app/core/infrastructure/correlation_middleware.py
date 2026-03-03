import hashlib
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.infrastructure.logging_config import (
    CONVERSATION_ID,
    PROJECT_ID,
    SESSION_ID,
    TRACE_ID,
    USER_ID,
)

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
except Exception:
    _OTEL = False


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        traceparent = request.headers.get("traceparent")
        tracestate = request.headers.get("tracestate")
        if not traceparent:
            traceparent = self._fallback_traceparent(request_id)
        try:
            actor = getattr(request.state, "actor_user_id", None)
        except Exception:
            actor = None
        user_id = (
            (str(actor) if actor is not None else None) or request.headers.get("X-User-Id") or None
        )
        session_id = request.headers.get("X-Session-Id") or None
        conversation_id = request.headers.get("X-Conversation-Id") or None
        project_id = request.headers.get("X-Project-Id") or None

        structlog.contextvars.clear_contextvars()
        bind_kwargs = {"request_id": request_id}
        if user_id is not None:
            bind_kwargs["user_id"] = user_id
        if session_id is not None:
            bind_kwargs["session_id"] = session_id
        if conversation_id is not None:
            bind_kwargs["conversation_id"] = conversation_id
        if project_id is not None:
            bind_kwargs["project_id"] = project_id
        structlog.contextvars.bind_contextvars(**bind_kwargs)
        try:
            TRACE_ID.set(request_id)
        except Exception:
            pass
        try:
            if user_id is not None:
                USER_ID.set(user_id)
        except Exception:
            pass
        try:
            if session_id is not None:
                SESSION_ID.set(session_id)
        except Exception:
            pass
        try:
            if conversation_id is not None:
                CONVERSATION_ID.set(conversation_id)
        except Exception:
            pass
        try:
            if project_id is not None:
                PROJECT_ID.set(project_id)
        except Exception:
            pass
        try:
            if _OTEL:
                span = trace.get_current_span()
                if span is not None:
                    span.set_attribute("janus.trace_id", request_id)
                    span.set_attribute("janus.traceparent", traceparent)
                    if tracestate is not None:
                        span.set_attribute("janus.tracestate", tracestate)
                    if user_id is not None:
                        span.set_attribute("janus.user_id", user_id)
                    if session_id is not None:
                        span.set_attribute("janus.session_id", session_id)
                    if conversation_id is not None:
                        span.set_attribute("janus.conversation_id", conversation_id)
                    if project_id is not None:
                        span.set_attribute("janus.project_id", project_id)
        except Exception:
            pass
        try:
            request.state.correlation_id = request_id
            request.state.traceparent = traceparent
            request.state.tracestate = tracestate
            request.state.session_id = session_id
            request.state.conversation_id = conversation_id
            request.state.project_id = project_id
        except Exception:
            pass

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["traceparent"] = traceparent
        if tracestate:
            response.headers["tracestate"] = tracestate
        return response

    def _fallback_traceparent(self, request_id: str) -> str:
        trace_id = hashlib.sha256(str(request_id).encode("utf-8")).hexdigest()[:32]
        span_id = trace_id[:16]
        return f"00-{trace_id}-{span_id}-01"
