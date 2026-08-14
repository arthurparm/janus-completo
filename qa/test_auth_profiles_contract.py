from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import jwt
import pytest
from app.core.infrastructure import auth
from app.core.security.actor_context import ActorContext, ActorType
from app.core.security.containment_middleware import SecurityContainmentMiddleware
from app.core.security.request_guard import require_human_admin_actor_context
from app.core.security.route_policy import (
    ApiProfile,
    EndpointPolicy,
    OwnershipMode,
    PrincipalType,
    apply_endpoint_policy_manifest,
    load_endpoint_policy_manifest,
    policy_openapi_extra,
    validate_route_policy,
)
from app.models.user_models import ExternalIdentity, ExternalIdentityEvent, User
from app.repositories.user_repository import (
    IdentityLinkRequiredError,
    InactivePrincipalError,
    UserRepository,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _claims(**changes):
    now = int(time.time())
    value = {
        "sub": "user-a",
        "iss": "https://issuer.example",
        "aud": "janus-user-api",
        "exp": now + 300,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "typ": "at+jwt",
    }
    value.update(changes)
    return value


def test_canonical_endpoint_manifest_is_complete_and_bijective():
    from app.main import app

    manifest = load_endpoint_policy_manifest()
    assert len({(policy.method, policy.path) for policy in manifest}) == len(manifest)
    assert len({policy.operation_id for policy in manifest}) == len(manifest)
    assert set(app.state.route_policy_matrix) == set(manifest)


def test_endpoint_manifest_rejects_route_or_policy_without_counterpart():
    route_only = FastAPI()

    @route_only.get("/unclassified", operation_id="unclassified")
    def unclassified():
        return {"ok": True}

    with pytest.raises(RuntimeError, match="route without policy"):
        apply_endpoint_policy_manifest(route_only, ())

    policy_only = FastAPI()
    policy = EndpointPolicy(
        method="GET",
        path="/missing",
        profile=ApiProfile.PUBLIC,
        principals=frozenset({PrincipalType.ANONYMOUS}),
        scopes=frozenset(),
        ownership=OwnershipMode.NONE,
        operation_id="missing",
    )
    with pytest.raises(RuntimeError, match="policy without route"):
        apply_endpoint_policy_manifest(policy_only, (policy,))


def test_rs256_validator_rejects_algorithm_confusion_and_invalid_claims(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _Client:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda *_: _Client())

    def encode(claims, *, algorithm="RS256", key=private_key, headers=None):
        return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": "key-1", **(headers or {})})

    valid = encode(_claims())
    assert auth._decode_external(
        valid,
        issuer="https://issuer.example",
        audience="janus-user-api",
        jwks_url="https://issuer.example/jwks",
        max_ttl_seconds=600,
    )["sub"] == "user-a"

    rejected = [
        encode(_claims(exp=int(time.time()) - 60)),
        encode(_claims(nbf=int(time.time()) + 300)),
        encode(_claims(iss="https://wrong.example")),
        encode(_claims(aud="wrong-audience")),
        encode(_claims(aud=["janus-user-api", "another-api"])),
        encode(_claims(typ="JWT")),
        encode(_claims(jti="")),
        encode(_claims(exp=int(time.time()) + 900)),
        jwt.encode(
            _claims(),
            "symmetric-secret-that-is-at-least-32-bytes",
            algorithm="HS256",
            headers={"kid": "key-1"},
        ),
        jwt.encode(_claims(), key="", algorithm="none", headers={"kid": "key-1"}),
        "malformed.token",
    ]
    header, payload, signature = valid.split(".")
    signature_index = len(signature) // 2
    altered_signature = (
        signature[:signature_index]
        + ("A" if signature[signature_index] != "A" else "B")
        + signature[signature_index + 1 :]
    )
    rejected.append(f"{header}.{payload}.{altered_signature}")
    rejected.append(encode(_claims(), headers={"jku": "https://attacker.invalid/jwks"}))
    rejected.append(jwt.encode(_claims(), private_key, algorithm="RS256"))
    for token in rejected:
        with pytest.raises(auth.TokenValidationError):
            auth._decode_external(
                token,
                issuer="https://issuer.example",
                audience="janus-user-api",
                jwks_url="https://issuer.example/jwks",
                max_ttl_seconds=600,
            )


def test_service_identity_requires_registered_client_audience_and_scopes(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _Client:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda *_: _Client())
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_ISSUER", "https://issuer.example")
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_JWKS_URL", "https://issuer.example/jwks")
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_AUDIENCE", "janus-control-plane")
    monkeypatch.setattr(
        auth.settings, "OIDC_SERVICE_PRINCIPALS", {"janus-worker": ["ops:read"]}
    )

    valid_claims = _claims(
        sub="janus-worker",
        aud="janus-control-plane",
        client_id="janus-worker",
        azp="janus-worker",
        scope="ops:read",
    )
    valid = jwt.encode(
        valid_claims, private_key, algorithm="RS256", headers={"kid": "service-key"}
    )
    actor = auth._authenticate_service(
        valid,
        trace_id="trace-service",
        request=SimpleNamespace(headers={}),
    )
    assert actor.actor_type is ActorType.SERVICE
    assert actor.client_id == "janus-worker"
    assert actor.scopes == ("ops:read",)

    for changes in (
        {"aud": "janus-user-api"},
        {"scope": "ops:read tools:admin"},
        {"sub": "different-subject"},
    ):
        rejected = jwt.encode(
            {**valid_claims, **changes},
            private_key,
            algorithm="RS256",
            headers={"kid": "service-key"},
        )
        with pytest.raises(auth.TokenValidationError):
            auth._authenticate_service(
                rejected,
                trace_id="trace-service",
                request=SimpleNamespace(headers={}),
            )


def test_admin_facade_delegation_must_match_active_audit_record(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _Client:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda *_: _Client())
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_ISSUER", "https://issuer.example")
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_JWKS_URL", "https://issuer.example/jwks")
    monkeypatch.setattr(auth.settings, "OIDC_SERVICE_AUDIENCE", "janus-control-plane")
    monkeypatch.setattr(auth.settings, "ADMIN_FACADE_CLIENT_ID", "janus-admin-facade")
    monkeypatch.setattr(
        auth.settings,
        "OIDC_SERVICE_PRINCIPALS",
        {"janus-admin-facade": ["identity:admin"]},
    )
    delegation_id = str(uuid.uuid4())
    token = jwt.encode(
        _claims(
            sub="janus-admin-facade",
            aud="janus-control-plane",
            client_id="janus-admin-facade",
            azp="janus-admin-facade",
            scope="identity:admin",
        ),
        private_key,
        algorithm="RS256",
        headers={"kid": "facade-key"},
    )
    request = SimpleNamespace(
        headers={
            "X-Janus-Delegated-Subject": "human-admin-subject",
            "X-Janus-Delegation-ID": delegation_id,
        },
        state=SimpleNamespace(
            endpoint_policy=SimpleNamespace(operation_id="get_user")
        ),
    )
    monkeypatch.setattr(
        UserRepository,
        "has_active_admin_delegation",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(auth.TokenValidationError, match="token validation failed"):
        auth._authenticate_service(token, trace_id="trace-admin", request=request)

    monkeypatch.setattr(
        UserRepository,
        "has_active_admin_delegation",
        lambda *_args, **_kwargs: True,
    )
    actor = auth._authenticate_service(token, trace_id="trace-admin", request=request)
    assert actor.delegation_id == delegation_id
    assert actor.delegated_subject == "human-admin-subject"


def test_profile_persona_matrix_and_unclassified_startup_failure(monkeypatch):
    app = FastAPI()
    app.add_middleware(SecurityContainmentMiddleware)
    monkeypatch.setattr(
        "app.core.security.containment_middleware.record_security_denial", lambda **_: None
    )

    actors = {
        "user-a": ActorContext.authenticated(
            actor_id="1", roles=("USER",), auth_method="oidc", trace_id="a"
        ),
        "user-b": ActorContext.authenticated(
            actor_id="2", roles=("USER",), auth_method="oidc", trace_id="b"
        ),
        "admin": ActorContext.authenticated(
            actor_id="3", roles=("USER", "ADMIN"), auth_method="oidc", trace_id="admin"
        ),
        "service": ActorContext.authenticated(
            actor_id="janus-worker",
            actor_type=ActorType.SERVICE,
            roles=("SERVICE",),
            auth_method="client_credentials",
            trace_id="svc",
            scopes=("ops:read",),
            client_id="janus-worker",
        ),
        "service-no-scope": ActorContext.authenticated(
            actor_id="janus-limited",
            actor_type=ActorType.SERVICE,
            roles=("SERVICE",),
            auth_method="client_credentials",
            trace_id="svc2",
        ),
    }

    def actor_for(request):
        value = (request.headers.get("Authorization") or "").removeprefix("Bearer ")
        return actors.get(value)

    monkeypatch.setattr("app.core.security.containment_middleware.get_actor_context", actor_for)
    resources = {"owned": "1"}

    @app.get(
        "/public",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.PUBLIC, principals={PrincipalType.ANONYMOUS}
        ),
    )
    async def public():
        return {"ok": True}

    @app.get(
        "/resources/{resource_id}",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.USER,
            principals={PrincipalType.USER},
            ownership=OwnershipMode.ACTOR,
        ),
    )
    async def resource(resource_id: str, request: Request):
        actor = request.state.actor_context
        if resources.get(resource_id) != actor.actor_id:
            return JSONResponse({"detail": "Not found"}, 404)
        return {"id": resource_id}

    @app.get(
        "/control",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.CONTROL_PLANE,
            principals={PrincipalType.SERVICE},
            scopes={"ops:read"},
        ),
    )
    async def control():
        return {"ok": True}

    @app.post(
        "/resources",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.USER,
            principals={PrincipalType.USER},
            ownership=OwnershipMode.ACTOR,
        ),
    )
    async def create_resource():
        return {"ok": True}

    @app.post(
        "/admin-actions",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.USER,
            principals={PrincipalType.USER},
            ownership=OwnershipMode.ACTOR,
        ),
    )
    async def admin_action(request: Request):
        require_human_admin_actor_context(request)
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/public").status_code == 200
    assert client.get("/resources/owned").status_code == 401
    assert client.get("/resources/owned", headers={"Authorization": "Bearer user-a"}).status_code == 200
    assert client.get("/resources/owned", headers={"Authorization": "Bearer user-b"}).status_code == 404
    assert client.get("/resources/owned", headers={"Authorization": "Bearer service"}).status_code == 403
    assert client.get("/control", headers={"Authorization": "Bearer admin"}).status_code == 403
    assert client.get("/control").status_code == 401
    assert client.get("/control", headers={"Authorization": "Bearer service"}).status_code == 200
    assert client.get("/control", headers={"Authorization": "Bearer service-no-scope"}).status_code == 403
    assert client.post("/resources", headers={"Authorization": "Bearer user-a"}, json={"owner_id": 1}).status_code == 400
    assert client.post("/admin-actions", headers={"Authorization": "Bearer user-a"}).status_code == 403
    assert client.post("/admin-actions", headers={"Authorization": "Bearer admin"}).status_code == 200
    assert client.post("/missing", json={"user_id": 1}).status_code == 404
    validate_route_policy(app)

    unclassified = FastAPI()

    @unclassified.get("/forgotten")
    async def forgotten():
        return {}

    with pytest.raises(RuntimeError, match="explicit policy"):
        validate_route_policy(unclassified)


def test_jit_is_single_use_under_concurrency_and_never_links_by_email(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'jit.db'}", connect_args={"check_same_thread": False}
    )
    User.__table__.create(engine)
    ExternalIdentity.__table__.create(engine)
    ExternalIdentityEvent.__table__.create(engine)
    sessions = sessionmaker(bind=engine)

    def provision():
        session = sessions()
        try:
            return UserRepository(session).resolve_or_provision_external_identity(
                issuer="https://issuer.example",
                subject="same-subject",
                email=None,
                email_verified=False,
                display_name="Same user",
            )[0].id
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: provision(), range(2)))
    assert ids[0] == ids[1]
    session = sessions()
    try:
        assert session.query(User).count() == 1
        assert session.query(ExternalIdentity).count() == 1
        assert session.query(ExternalIdentityEvent).count() == 1
        provisioned = session.query(User).filter(User.id == ids[0]).one()
        provisioned.status = "suspended"
        session.commit()
        with pytest.raises(InactivePrincipalError):
            UserRepository(session).resolve_or_provision_external_identity(
                issuer="https://issuer.example",
                subject="same-subject",
                email=None,
                email_verified=False,
                display_name=None,
            )
        provisioned.status = "active"
        session.commit()
        existing = User(email="verified@example.com", status="active")
        session.add(existing)
        session.commit()
        with pytest.raises(IdentityLinkRequiredError):
            UserRepository(session).resolve_or_provision_external_identity(
                issuer="https://issuer.example",
                subject="different-subject",
                email="verified@example.com",
                email_verified=True,
                display_name=None,
            )
    finally:
        session.close()


def test_admin_facade_requests_only_the_target_operation_scopes(monkeypatch):
    from app.api.v1.endpoints import admin_actions

    captured: dict[str, object] = {}

    class _Response:
        status_code = 200

        def json(self):
            return {"access_token": "service-token"}

    class _Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, data, auth):
            captured.update(url=url, data=data, auth=auth)
            return _Response()

    monkeypatch.setattr(admin_actions.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(admin_actions.settings, "OIDC_SERVICE_TOKEN_URL", "https://idp.example/token")
    monkeypatch.setattr(admin_actions.settings, "OIDC_SERVICE_AUDIENCE", "janus-control-plane")
    monkeypatch.setattr(admin_actions.settings, "ADMIN_FACADE_CLIENT_ID", "janus-admin-facade")
    monkeypatch.setattr(
        admin_actions.settings,
        "ADMIN_FACADE_CLIENT_SECRET",
        SecretStr("facade-secret"),
    )

    token = asyncio.run(
        admin_actions._service_token(frozenset({"deployment:write", "ops:read"}))
    )

    assert token == "service-token"
    assert captured["data"] == {
        "grant_type": "client_credentials",
        "audience": "janus-control-plane",
        "scope": "deployment:write ops:read",
    }
    assert captured["auth"] == ("janus-admin-facade", SecretStr("facade-secret").get_secret_value())


def test_admin_facade_rejects_arbitrary_transport_and_query_parameters():
    from app.api.v1.endpoints.admin_actions import AdminActionRequest, _validate_query_params
    from fastapi import HTTPException
    from fastapi.routing import APIRoute
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AdminActionRequest(operation_id="safe_operation", method="DELETE", url="https://evil.invalid")

    app = FastAPI()

    @app.get("/items")
    async def items(limit: int = 20):
        return {"limit": limit}

    route = next(route for route in app.routes if isinstance(route, APIRoute))
    _validate_query_params(route, {"limit": "5"})
    with pytest.raises(HTTPException) as unknown:
        _validate_query_params(route, {"target_url": "https://evil.invalid"})
    assert unknown.value.status_code == 400
    with pytest.raises(HTTPException) as malformed:
        _validate_query_params(route, {"limit": "not-an-integer"})
    assert malformed.value.status_code == 422
