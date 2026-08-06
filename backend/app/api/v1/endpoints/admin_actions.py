from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import quote

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.config import settings
from app.core.security.request_guard import require_human_admin_actor_context
from app.core.security.route_policy import ApiProfile, EndpointPolicy
from app.db import db

router = APIRouter(tags=["Admin Actions"])
_PATH_PARAMETER = re.compile(r"{([^}:]+)(?::[^}]+)?}")
logger = structlog.get_logger(__name__)


class AdminActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(..., min_length=1, max_length=255)
    path_params: dict[str, str | int] = Field(default_factory=dict)
    query_params: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


def _target_policy(request: Request, operation_id: str) -> EndpointPolicy:
    matches: list[EndpointPolicy] = [
        policy
        for policy in request.app.state.route_policy_matrix
        if policy.operation_id == operation_id
        and policy.profile is ApiProfile.CONTROL_PLANE
        and policy.human_delegable
    ]
    if len(matches) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operation")
    return matches[0]


def _target_path(policy: EndpointPolicy, values: dict[str, str | int]) -> str:
    required = set(_PATH_PARAMETER.findall(policy.path))
    if set(values) != required:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path parameters")
    path = policy.path
    for name in required:
        path = re.sub(
            r"{" + re.escape(name) + r"(?::[^}]+)?}",
            quote(str(values[name]), safe=""),
            path,
        )
    return path


def _target_route(request: Request, policy: EndpointPolicy) -> APIRoute:
    routes = [
        route
        for route in request.app.state.all_profile_routes
        if isinstance(route, APIRoute)
        and str(route.operation_id or route.unique_id) == policy.operation_id
    ]
    if len(routes) != 1:
        raise HTTPException(status_code=400, detail="Invalid operation contract")
    return routes[0]


def _validate_operation_payload(route: APIRoute, value: dict[str, Any]) -> None:
    body_field = route.body_field
    if body_field is None:
        if value:
            raise HTTPException(status_code=400, detail="Operation does not accept a body")
        return
    _, errors = body_field.validate(value, {}, loc=("body",))
    if errors:
        raise HTTPException(status_code=422, detail=errors)


def _validate_query_params(route: APIRoute, values: dict[str, Any]) -> None:
    fields = {str(field.alias): field for field in route.dependant.query_params}
    unknown = set(values) - set(fields)
    if unknown:
        raise HTTPException(status_code=400, detail="Invalid query parameters")
    errors: list[Any] = []
    for alias, field in fields.items():
        if alias not in values:
            if field.required:
                errors.append({"loc": ["query", alias], "msg": "Field required", "type": "missing"})
            continue
        _, field_errors = field.validate(values[alias], {}, loc=("query", alias))
        if field_errors:
            if isinstance(field_errors, list):
                errors.extend(field_errors)
            else:
                errors.append(field_errors)
    if errors:
        raise HTTPException(status_code=422, detail=errors)


async def _service_token(required_scopes: frozenset[str]) -> str:
    if not settings.OIDC_SERVICE_TOKEN_URL.lower().startswith("https://"):
        raise HTTPException(status_code=503, detail="Administrative service identity unavailable")
    if settings.ADMIN_FACADE_CLIENT_SECRET is None:
        raise HTTPException(status_code=503, detail="Administrative service identity unavailable")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.OIDC_SERVICE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "audience": settings.OIDC_SERVICE_AUDIENCE,
                "scope": " ".join(sorted(required_scopes)),
            },
            auth=(
                settings.ADMIN_FACADE_CLIENT_ID,
                settings.ADMIN_FACADE_CLIENT_SECRET.get_secret_value(),
            ),
        )
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Administrative service identity unavailable")
    token = str(response.json().get("access_token") or "")
    if not token:
        raise HTTPException(status_code=503, detail="Administrative service identity unavailable")
    return token


def _begin_delegation(
    *,
    delegation_id: str,
    human_issuer: str,
    human_subject: str,
    operation_id: str,
    resource_id: str | None,
    trace_id: str,
) -> None:
    session = db.get_session_direct()
    try:
        session.execute(
            text(
                """
                INSERT INTO admin_delegations(
                    id, human_issuer, human_subject, service_client_id, operation_id,
                    resource_id, result_status, trace_id
                ) VALUES (
                    :id, :human_issuer, :human_subject, :service_client_id, :operation_id,
                    :resource_id, NULL, :trace_id
                )
                """
            ),
            {
                "id": delegation_id,
                "human_issuer": human_issuer,
                "human_subject": human_subject,
                "service_client_id": settings.ADMIN_FACADE_CLIENT_ID,
                "operation_id": operation_id,
                "resource_id": resource_id,
                "trace_id": trace_id,
            },
        )
        session.commit()
    finally:
        session.close()


def _complete_delegation(*, delegation_id: str, result_status: int) -> None:
    session = db.get_session_direct()
    try:
        session.execute(
            text(
                """
                UPDATE admin_delegations
                SET result_status = :result_status
                WHERE id = :id AND result_status IS NULL
                """
            ),
            {"id": delegation_id, "result_status": result_status},
        )
        session.commit()
    except Exception:
        session.rollback()
        logger.exception(
            "admin_delegation_result_audit_failed",
            delegation_id=delegation_id,
            result_status=result_status,
        )
    finally:
        session.close()


@router.post("/admin-actions", operation_id="execute_admin_action")
async def execute_admin_action(payload: AdminActionRequest, request: Request) -> Response:
    actor = require_human_admin_actor_context(request)
    policy = _target_policy(request, payload.operation_id)
    target_path = _target_path(policy, payload.path_params)
    route = _target_route(request, policy)
    _validate_operation_payload(route, payload.payload)
    _validate_query_params(route, payload.query_params)
    delegation_id = str(uuid.uuid4())
    resource_id = next(iter(payload.path_params.values()), None)
    _begin_delegation(
        delegation_id=delegation_id,
        human_issuer=str(actor.issuer),
        human_subject=str(actor.subject),
        operation_id=policy.operation_id,
        resource_id=str(resource_id) if resource_id is not None else None,
        trace_id=actor.trace_id,
    )
    try:
        token = await _service_token(policy.scopes)
    except HTTPException as exc:
        _complete_delegation(delegation_id=delegation_id, result_status=exc.status_code)
        raise
    target_url = settings.CONTROL_PLANE_BASE_URL.rstrip("/") + target_path
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Janus-Delegation-ID": delegation_id,
        "X-Janus-Delegated-Subject": str(actor.subject),
        "X-Request-ID": actor.trace_id,
        "Idempotency-Key": delegation_id,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                policy.method,
                target_url,
                json=payload.payload if policy.method in {"POST", "PUT", "PATCH"} else None,
                params=payload.query_params,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        _complete_delegation(delegation_id=delegation_id, result_status=502)
        raise HTTPException(status_code=502, detail="Control-plane unavailable") from exc
    _complete_delegation(delegation_id=delegation_id, result_status=response.status_code)
    content_type = response.headers.get("content-type", "application/octet-stream")
    if "json" in content_type.lower():
        try:
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except ValueError:
            return JSONResponse(
                content={"detail": "Control-plane returned invalid JSON"},
                status_code=502,
            )
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=content_type.split(";", 1)[0],
    )
