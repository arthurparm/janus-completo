from types import SimpleNamespace

import pytest
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod
from app.core.security.request_guard import (
    require_human_admin_actor_context,
    require_service_actor,
)
from fastapi import HTTPException


def _request(actor: ActorContext):
    return SimpleNamespace(
        state=SimpleNamespace(actor_context=actor),
        headers={},
    )


def test_human_admin_is_derived_from_oidc_actor_context():
    actor = ActorContext.authenticated(
        actor_id=42,
        roles=("ADMIN", "USER"),
        auth_method=AuthMethod.OIDC,
        trace_id="human-admin",
        groups=("janus-admins",),
    )
    assert require_human_admin_actor_context(_request(actor)) is actor


def test_human_admin_rejects_service_identity():
    actor = ActorContext.authenticated(
        actor_id="janus-worker",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="service",
    )
    with pytest.raises(HTTPException) as exc:
        require_human_admin_actor_context(_request(actor))
    assert exc.value.status_code == 403


def test_service_guard_rejects_human_admin():
    actor = ActorContext.authenticated(
        actor_id=42,
        roles=("ADMIN", "USER"),
        auth_method=AuthMethod.OIDC,
        trace_id="human-admin",
    )
    with pytest.raises(HTTPException) as exc:
        require_service_actor(_request(actor))
    assert exc.value.status_code == 403


def test_service_guard_accepts_service_identity():
    actor = ActorContext.authenticated(
        actor_id="janus-worker",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="service",
    )
    assert require_service_actor(_request(actor)) == "janus-worker"
