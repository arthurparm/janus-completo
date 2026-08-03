from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from fastapi import FastAPI
from starlette.routing import BaseRoute, Route


class AccessLevel(StrEnum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    OWNER = "owner"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class RoutePolicy:
    methods: frozenset[str]
    path: str
    access: AccessLevel


PUBLIC_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/health"),
        ("GET", "/healthz"),
        ("POST", "/api/v1/auth/local/login"),
        ("POST", "/api/v1/auth/local/refresh"),
        ("POST", "/api/v1/auth/local/request-reset"),
        ("POST", "/api/v1/auth/local/reset"),
        ("POST", "/api/v1/auth/firebase/exchange"),
        ("POST", "/api/v1/auth/supabase/exchange"),
    }
)

ADMIN_PREFIXES: tuple[str, ...] = (
    "/api/v1/admin",
    "/api/v1/autonomy",
    "/api/v1/deployment",
    "/api/v1/governance",
    "/api/v1/learning",
    "/api/v1/knowledge/experimental",
    "/api/v1/observability",
    "/api/v1/system",
    "/api/v1/tools",
    "/api/v1/users",
    "/api/v1/workers",
    "/metrics",
)

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def classify_operation(method: str, path: str) -> AccessLevel:
    normalized_method = method.upper()
    if (normalized_method, path) in PUBLIC_OPERATIONS:
        return AccessLevel.PUBLIC
    if any(path.startswith(prefix) for prefix in ADMIN_PREFIXES):
        return AccessLevel.ADMIN
    return AccessLevel.AUTHENTICATED


def build_route_policy_matrix(routes: Iterable[BaseRoute]) -> tuple[RoutePolicy, ...]:
    matrix: list[RoutePolicy] = []
    for route in routes:
        if not isinstance(route, Route):
            continue
        methods = frozenset(str(method).upper() for method in (route.methods or set()))
        for method in methods:
            matrix.append(
                RoutePolicy(
                    methods=frozenset({method}),
                    path=route.path,
                    access=classify_operation(method, route.path),
                )
            )
    return tuple(matrix)


def validate_route_policy(app: FastAPI) -> tuple[RoutePolicy, ...]:
    matrix = build_route_policy_matrix(app.routes)
    violations = [
        f"{next(iter(policy.methods))} {policy.path}"
        for policy in matrix
        if policy.access is AccessLevel.PUBLIC
        and next(iter(policy.methods)) in MUTATING_METHODS
        and (next(iter(policy.methods)), policy.path) not in PUBLIC_OPERATIONS
    ]
    public_mutations = [
        f"{method} {path}"
        for method, path in PUBLIC_OPERATIONS
        if method in MUTATING_METHODS and not path.startswith("/api/v1/auth/")
    ]
    if violations or public_mutations:
        raise RuntimeError(
            "route policy invariant failed: " + ", ".join(sorted(violations + public_mutations))
        )
    return matrix
