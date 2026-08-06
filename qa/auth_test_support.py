from __future__ import annotations

from app.core.security.actor_context import ActorContext, AuthMethod

_PREFIX = "test-actor:"


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
