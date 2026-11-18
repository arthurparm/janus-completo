from __future__ import annotations

from app.core.security.actor_context import ActorContext, ActorType, AuthMethod

_PREFIX = "test-actor:"
_SERVICE_PREFIX = "test-service-actor:"


def issue_test_actor_token(user_id: int | str) -> str:
    """Opaque test credential consumed only by explicit test middleware patches."""
    return f"{_PREFIX}{user_id}"


def decode_test_actor_id(token: str) -> int | None:
    if not token.startswith(_PREFIX):
        return None
    try:
        return int(token.removeprefix(_PREFIX))
    except ValueError:
        return None


def actor_from_test_request(request) -> ActorContext | None:
    authorization = str(request.headers.get("Authorization") or "")
    if not authorization.startswith("Bearer "):
        return None
    actor_id = decode_test_actor_id(authorization.removeprefix("Bearer "))
    if actor_id is None:
        return None
    return ActorContext.authenticated(
        actor_id=actor_id,
        roles=("USER",),
        auth_method=AuthMethod.OIDC,
        trace_id="test-actor",
        issuer="https://test-idp.invalid",
        subject=f"test-subject-{actor_id}",
    )


def issue_test_service_token(client_id: str, scopes: tuple[str, ...] = ()) -> str:
    """Opaque test credential for a control-plane service actor, consumed only by explicit test middleware patches."""
    return f"{_SERVICE_PREFIX}{client_id}:{','.join(scopes)}"


def service_actor_from_test_request(request) -> ActorContext | None:
    authorization = str(request.headers.get("Authorization") or "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    if not token.startswith(_SERVICE_PREFIX):
        return None
    client_id, _, scope_str = token.removeprefix(_SERVICE_PREFIX).partition(":")
    scopes = tuple(scope for scope in scope_str.split(",") if scope)
    return ActorContext.authenticated(
        actor_id=client_id,
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="test-service-actor",
        scopes=scopes,
        client_id=client_id,
    )


def any_actor_from_test_request(request) -> ActorContext | None:
    """Resolves either a user or a service test actor, whichever prefix matches the bearer token."""
    return actor_from_test_request(request) or service_actor_from_test_request(request)
