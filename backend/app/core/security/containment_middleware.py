from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.config import settings
from app.core.infrastructure.auth import get_actor_context
from app.core.security.actor_context import CURRENT_ACTOR_CONTEXT, ActorContext, ActorType
from app.core.security.route_policy import PrincipalType, resolve_endpoint_policy
from app.core.security.security_audit import record_security_denial
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_FORBIDDEN_IDENTITY_KEYS = frozenset(
    {
        "userid",
        "actoruserid",
        "authuserid",
        "requesterid",
        "principalid",
        "ownerid",
        "identity",
        "sub",
        "subjectid",
    }
)
_FORBIDDEN_HEADERS = frozenset(
    {"x-user-id", "x-actor-user-id", "x-project-id", "x-owner-id", "x-identity", "x-subject"}
)
_MULTIPART_NAME = re.compile(rb'name="([^"]+)"', re.IGNORECASE)


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _contains_forbidden_identity(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalized_key(str(key)) in _FORBIDDEN_IDENTITY_KEYS:
                return True
            if _contains_forbidden_identity(child):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_identity(child) for child in value)
    return False


def _is_loopback(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


class SecurityContainmentMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    async def _blocked(
        self,
        request: Request,
        *,
        actor: ActorContext | None,
        status_code: int,
        reason: str,
        detail: str,
        error_code: str | None = None,
    ) -> JSONResponse:
        trace_id = str(getattr(request.state, "trace_id", "") or uuid.uuid4().hex)
        record_security_denial(
            method=request.method,
            route=request.url.path,
            reason=reason,
            trace_id=trace_id,
            actor=actor,
            status_code=status_code,
        )
        payload: dict[str, Any] = {"detail": detail, "trace_id": trace_id}
        if error_code:
            payload["code"] = error_code
        headers = {"WWW-Authenticate": 'Bearer realm="janus"'} if status_code == 401 else None
        return JSONResponse(payload, status_code=status_code, headers=headers)

    async def _reject_client_identity(self, request: Request) -> bool:
        if any(name.lower() in _FORBIDDEN_HEADERS for name in request.headers.keys()):
            return True
        if any(_normalized_key(key) in _FORBIDDEN_IDENTITY_KEYS for key in request.query_params.keys()):
            return True

        content_type = (request.headers.get("content-type") or "").lower()
        if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return False
        if "application/json" not in content_type and "multipart/form-data" not in content_type:
            return False

        body = await request.body()
        if not body:
            return False
        if "application/json" in content_type:
            try:
                return _contains_forbidden_identity(json.loads(body))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False
        return any(
            _normalized_key(match.decode("utf-8", errors="ignore")) in _FORBIDDEN_IDENTITY_KEYS
            for match in _MULTIPART_NAME.findall(body)
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.trace_id = str(
            getattr(request.state, "trace_id", "")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex
        )
        path = request.url.path
        environment = str(settings.ENVIRONMENT).strip().lower()
        if path in {"/docs", "/redoc", "/openapi.json"}:
            if environment != "development" or not _is_loopback(request):
                return await self._blocked(
                    request,
                    actor=None,
                    status_code=403,
                    reason="api_documentation_restricted",
                    detail="Forbidden",
                )

        if request.method == "OPTIONS":
            return await call_next(request)

        policy = resolve_endpoint_policy(request)
        if policy is None:
            return await call_next(request)

        if await self._reject_client_identity(request):
            return await self._blocked(
                request,
                actor=None,
                status_code=400,
                reason="client_identity_field_forbidden",
                detail="Client-supplied identity fields are forbidden",
                error_code="CLIENT_IDENTITY_FIELD_FORBIDDEN",
            )

        request.state.endpoint_policy = policy
        actor = get_actor_context(request)
        request.state.actor_context = actor
        token = CURRENT_ACTOR_CONTEXT.set(actor)
        try:
            if PrincipalType.ANONYMOUS in policy.principals:
                return await call_next(request)
            if actor is None:
                return await self._blocked(
                    request,
                    actor=None,
                    status_code=401,
                    reason="authentication_required",
                    detail="Authentication required",
                )
            expected_type = (
                ActorType.HUMAN
                if PrincipalType.USER in policy.principals
                else ActorType.SERVICE
            )
            if actor.actor_type is not expected_type:
                return await self._blocked(
                    request,
                    actor=actor,
                    status_code=403,
                    reason="principal_type_not_allowed",
                    detail="Forbidden",
                )
            if expected_type is ActorType.SERVICE and not actor.has_scopes(policy.scopes):
                return await self._blocked(
                    request,
                    actor=actor,
                    status_code=403,
                    reason="service_scope_required",
                    detail="Forbidden",
                )
            return await call_next(request)
        finally:
            CURRENT_ACTOR_CONTEXT.reset(token)
