from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from starlette.routing import Match


class ApiProfile(StrEnum):
    PUBLIC = "public"
    USER = "user"
    CONTROL_PLANE = "control-plane"
    ALL_TEST = "all-test"


class PrincipalType(StrEnum):
    ANONYMOUS = "anonymous"
    USER = "user"
    SERVICE = "service"


class OwnershipMode(StrEnum):
    NONE = "none"
    ACTOR = "actor"
    SELF = "self"


@dataclass(frozen=True, slots=True)
class EndpointPolicy:
    method: str
    path: str
    profile: ApiProfile
    principals: frozenset[PrincipalType]
    scopes: frozenset[str]
    ownership: OwnershipMode
    operation_id: str
    human_delegable: bool = False


POLICY_MANIFEST_PATH = Path(__file__).with_name("endpoint_policy_manifest.json")
CONTROL_PLANE_SCOPES = frozenset(
    {
        "identity:admin",
        "ops:read",
        "ops:execute",
        "deployment:write",
        "workers:manage",
        "governance:write",
        "autonomy:admin",
        "evaluation:ingest",
        "observability:read",
        "tools:admin",
    }
)


def policy_openapi_extra(
    *,
    profile: ApiProfile,
    principals: Iterable[PrincipalType],
    scopes: Iterable[str] = (),
    ownership: OwnershipMode = OwnershipMode.NONE,
    human_delegable: bool = False,
) -> dict[str, Any]:
    principal_set = set(principals)
    if principal_set == {PrincipalType.ANONYMOUS}:
        security: list[dict[str, list[str]]] = []
    elif principal_set == {PrincipalType.USER}:
        security = [{"OIDCUser": []}]
    else:
        security = [{"OIDCService": sorted(set(scopes))}]
    return {
        "security": security,
        "x-janus-security-profile": profile.value,
        "x-janus-principals": sorted(principal.value for principal in principal_set),
        "x-janus-scopes": sorted(set(scopes)),
        "x-janus-ownership": ownership.value,
        "x-janus-human-delegable": human_delegable,
    }


def _from_route(route: APIRoute, method: str) -> EndpointPolicy:
    extra = route.openapi_extra or {}
    try:
        return EndpointPolicy(
            method=method.upper(),
            path=route.path_format,
            profile=ApiProfile(extra["x-janus-security-profile"]),
            principals=frozenset(
                PrincipalType(value) for value in extra["x-janus-principals"]
            ),
            scopes=frozenset(str(value) for value in extra["x-janus-scopes"]),
            ownership=OwnershipMode(extra["x-janus-ownership"]),
            operation_id=str(route.operation_id or route.unique_id),
            human_delegable=bool(extra["x-janus-human-delegable"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"route has no valid explicit policy: {method} {route.path}") from exc


def load_endpoint_policy_manifest(
    path: Path = POLICY_MANIFEST_PATH,
) -> tuple[EndpointPolicy, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"endpoint policy manifest is unavailable: {path}") from exc
    if not isinstance(payload, list):
        raise RuntimeError("endpoint policy manifest must be a JSON array")

    expected_fields = {
        "method",
        "path",
        "profile",
        "principals",
        "scopes",
        "ownership",
        "operation_id",
        "human_delegable",
    }
    policies: list[EndpointPolicy] = []
    for index, record in enumerate(payload):
        if not isinstance(record, dict) or set(record) != expected_fields:
            raise RuntimeError(f"invalid endpoint policy manifest record at index {index}")
        try:
            policies.append(
                EndpointPolicy(
                    method=str(record["method"]).upper(),
                    path=str(record["path"]),
                    profile=ApiProfile(record["profile"]),
                    principals=frozenset(PrincipalType(value) for value in record["principals"]),
                    scopes=frozenset(str(value) for value in record["scopes"]),
                    ownership=OwnershipMode(record["ownership"]),
                    operation_id=str(record["operation_id"]),
                    human_delegable=bool(record["human_delegable"]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"invalid endpoint policy manifest record at index {index}"
            ) from exc
    return tuple(policies)


def _validate_policy_matrix(matrix: Iterable[EndpointPolicy]) -> tuple[str, ...]:
    keys: set[tuple[str, str]] = set()
    operation_ids: set[str] = set()
    errors: list[str] = []
    for policy in matrix:
        key = (policy.method, policy.path)
        if key in keys:
            errors.append(f"duplicate route: {policy.method} {policy.path}")
        keys.add(key)
        if not policy.operation_id:
            errors.append(f"missing operation id: {policy.method} {policy.path}")
        elif policy.operation_id in operation_ids:
            errors.append(f"duplicate operation id: {policy.operation_id}")
        operation_ids.add(policy.operation_id)
        if not policy.path.startswith("/"):
            errors.append(f"invalid path: {policy.method} {policy.path}")
        if policy.profile is ApiProfile.PUBLIC:
            if policy.method not in {"GET", "HEAD"}:
                errors.append(f"public mutation: {policy.method} {policy.path}")
            if policy.principals != {PrincipalType.ANONYMOUS}:
                errors.append(f"invalid public principal: {policy.method} {policy.path}")
            if policy.scopes or policy.ownership is not OwnershipMode.NONE:
                errors.append(f"invalid public authorization metadata: {policy.method} {policy.path}")
        elif policy.profile is ApiProfile.USER:
            if policy.principals != {PrincipalType.USER}:
                errors.append(f"invalid user principal: {policy.method} {policy.path}")
            if policy.ownership is OwnershipMode.NONE:
                errors.append(f"user route without ownership: {policy.method} {policy.path}")
            if policy.scopes:
                errors.append(f"user route with service scopes: {policy.method} {policy.path}")
        elif policy.profile is ApiProfile.CONTROL_PLANE:
            if policy.principals != {PrincipalType.SERVICE}:
                errors.append(f"invalid control-plane principal: {policy.method} {policy.path}")
            if not policy.scopes:
                errors.append(f"control-plane route without scope: {policy.method} {policy.path}")
            unknown_scopes = policy.scopes - CONTROL_PLANE_SCOPES
            if unknown_scopes:
                errors.append(
                    f"unknown control-plane scopes {sorted(unknown_scopes)!r}: "
                    f"{policy.method} {policy.path}"
                )
            if policy.ownership is not OwnershipMode.NONE:
                errors.append(f"control-plane route with ownership: {policy.method} {policy.path}")
        else:
            errors.append(f"invalid executable profile: {policy.method} {policy.path}")
        if policy.human_delegable and policy.profile is not ApiProfile.CONTROL_PLANE:
            errors.append(f"non-control route is human delegable: {policy.method} {policy.path}")
    return tuple(errors)


def apply_endpoint_policy_manifest(
    app: FastAPI,
    manifest: Iterable[EndpointPolicy] | None = None,
) -> tuple[EndpointPolicy, ...]:
    policies = tuple(
        load_endpoint_policy_manifest() if manifest is None else manifest
    )
    errors = list(_validate_policy_matrix(policies))
    policy_by_key = {(policy.method, policy.path): policy for policy in policies}
    route_by_key: dict[tuple[str, str], APIRoute] = {}
    for route in app.router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or ()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = (method, route.path_format)
            if key in route_by_key:
                errors.append(f"duplicate route: {method} {route.path_format}")
            route_by_key[key] = route

    for method, path in sorted(route_by_key.keys() - policy_by_key.keys()):
        errors.append(f"route without policy: {method} {path}")
    for method, path in sorted(policy_by_key.keys() - route_by_key.keys()):
        errors.append(f"policy without route: {method} {path}")
    for key in sorted(route_by_key.keys() & policy_by_key.keys()):
        route = route_by_key[key]
        policy = policy_by_key[key]
        route_operation_id = str(route.operation_id or route.unique_id)
        if route_operation_id != policy.operation_id:
            errors.append(
                f"operation id mismatch for {key[0]} {key[1]}: "
                f"route={route_operation_id} policy={policy.operation_id}"
            )

    if errors:
        raise RuntimeError("endpoint policy manifest invariant failed: " + "; ".join(errors))

    for key, route in route_by_key.items():
        policy = policy_by_key[key]
        route.openapi_extra = {
            **(route.openapi_extra or {}),
            **policy_openapi_extra(
                profile=policy.profile,
                principals=policy.principals,
                scopes=policy.scopes,
                ownership=policy.ownership,
                human_delegable=policy.human_delegable,
            ),
        }
    app.state.endpoint_policy_manifest = policies
    return policies


def build_route_policy_matrix(routes: Iterable[Any]) -> tuple[EndpointPolicy, ...]:
    matrix: list[EndpointPolicy] = []
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or ()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            matrix.append(_from_route(route, method))
    return tuple(matrix)


def validate_route_policy(app: FastAPI) -> tuple[EndpointPolicy, ...]:
    matrix = build_route_policy_matrix(app.routes)
    errors = list(_validate_policy_matrix(matrix))
    if errors:
        raise RuntimeError("route policy invariant failed: " + "; ".join(sorted(errors)))
    return matrix


def configure_profile_routes(app: FastAPI, profile: ApiProfile) -> tuple[EndpointPolicy, ...]:
    manifest = apply_endpoint_policy_manifest(app)
    matrix = validate_route_policy(app)
    if set(matrix) != set(manifest):
        raise RuntimeError("route policy manifest content does not match registered routes")
    app.state.all_profile_routes = tuple(
        route for route in app.router.routes if isinstance(route, APIRoute)
    )
    if profile is ApiProfile.ALL_TEST:
        return matrix
    app.router.routes = [
        route
        for route in app.router.routes
        if not isinstance(route, APIRoute)
        or _from_route(route, next(iter(route.methods or {"GET"}))).profile is profile
    ]
    app.openapi_schema = None
    validate_route_policy(app)
    return matrix


def resolve_endpoint_policy(request: Request) -> EndpointPolicy | None:
    scope = request.scope
    for route in request.app.router.routes:
        if not isinstance(route, APIRoute):
            continue
        match, _ = route.matches(scope)
        if match is Match.FULL and request.method.upper() in (route.methods or ()):
            return _from_route(route, request.method)
    return None
