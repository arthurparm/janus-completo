from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from app.config import settings
from app.core.infrastructure.auth import (
    create_actor_envelope,
    verify_actor_envelope,
)
from app.core.infrastructure.logging_config import _redact_secrets
from app.core.security.actor_context import ActorContext, ActorType
from app.core.security.authorization import authorization_service
from app.core.security.autonomy_guard import validate_autonomous_evolution_disabled
from app.core.security.containment_middleware import SecurityContainmentMiddleware
from app.core.security.redaction import REDACTION_FAILED, redact_sensitive_payload
from app.core.security.route_policy import (
    ApiProfile,
    OwnershipMode,
    PrincipalType,
    build_route_policy_matrix,
    policy_openapi_extra,
    validate_route_policy,
)
from app.core.security.security_alerts import emit_security_alert
from app.core.tools.action_module import PermissionLevel, ToolCategory, action_registry
from app.core.tools.production_manifest import register_production_tools
from app.repositories.observability_repository import _normalize_ledger_payload
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.tools import tool


def _actor() -> ActorContext:
    return ActorContext.authenticated(
        actor_id="7",
        roles=("USER",),
        auth_method="oidc",
        trace_id="trace-1",
    )


def test_actor_context_is_immutable_and_owner_binding_returns_copy():
    actor = _actor()
    with pytest.raises(dataclasses.FrozenInstanceError):
        actor.actor_id = "8"  # type: ignore[misc]
    bound = actor.bind_resource_owner("7")
    assert actor.resource_owner is None
    assert bound.resource_owner == "7"
    with pytest.raises(TypeError):
        ActorContext(  # type: ignore[call-arg]
            actor_id="7",
            actor_type=actor.actor_type,
            roles=actor.roles,
            auth_method=actor.auth_method,
            trace_id=actor.trace_id,
        )


def test_signed_actor_envelope_rejects_wrong_audience(monkeypatch):
    envelope = create_actor_envelope(_actor(), audience="janus-broker")
    verified = verify_actor_envelope(envelope, audience="janus-broker")
    assert verified is not None
    assert verified.actor_id == _actor().actor_id
    assert verify_actor_envelope(envelope, audience="other") is None


def test_authorization_service_separates_human_admin_and_service_identity():
    human_admin = ActorContext.authenticated(
        actor_id="7", roles=("ADMIN",), auth_method="oidc", trace_id="human-admin"
    )
    service = ActorContext.authenticated(
        actor_id="janus-worker",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method="client_credentials",
        trace_id="service",
    )
    assert authorization_service.require_human_admin(actor=human_admin) is human_admin
    assert authorization_service.require_service(actor=service) is service
    with pytest.raises(Exception) as denied_human:
        authorization_service.require_service(actor=human_admin)
    assert getattr(denied_human.value, "status_code", None) == 403
    with pytest.raises(Exception) as denied_service:
        authorization_service.require_human_admin(actor=service)
    assert getattr(denied_service.value, "status_code", None) == 403


def test_middleware_default_deny_and_client_identity_rejection(monkeypatch):
    app = FastAPI()
    app.add_middleware(SecurityContainmentMiddleware)
    monkeypatch.setattr(
        "app.core.security.containment_middleware.record_security_denial", lambda **_: None
    )
    monkeypatch.setattr("app.core.security.containment_middleware.get_actor_context", lambda _: None)

    @app.get(
        "/health",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.PUBLIC, principals={PrincipalType.ANONYMOUS}
        ),
    )
    async def health():
        return {"ok": True}

    @app.post(
        "/api/v1/items",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.USER,
            principals={PrincipalType.USER},
            ownership=OwnershipMode.ACTOR,
        ),
    )
    async def mutate():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.post("/api/v1/items", json={"name": "safe"}).status_code == 401
    assert client.post("/api/v1/items", json={"subject": "business subject"}).status_code == 401
    assert client.post("/api/v1/items", json={"sub": "forged-oidc-subject"}).status_code == 400
    assert client.post("/api/v1/items", json={"subject_id": "forged-subject"}).status_code == 400
    response = client.post("/api/v1/items", json={"nested": {"UsEr_Id": "99"}})
    assert response.status_code == 400
    assert response.json()["code"] == "CLIENT_IDENTITY_FIELD_FORBIDDEN"
    assert client.post("/api/v1/items?actor_user_id=99", json={}).status_code == 400
    assert client.post("/api/v1/items", headers={"X-Project-Id": "p1"}, json={}).status_code == 400
    assert (
        client.post(
            "/api/v1/items",
            files={"UsEr_Id": (None, "99")},
        ).status_code
        == 400
    )


def test_every_route_gets_a_policy_and_no_non_auth_mutation_is_public():
    app = FastAPI()

    @app.get(
        "/health",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.PUBLIC, principals={PrincipalType.ANONYMOUS}
        ),
    )
    async def health():
        return {}

    @app.post(
        "/api/v1/items",
        openapi_extra=policy_openapi_extra(
            profile=ApiProfile.USER,
            principals={PrincipalType.USER},
            ownership=OwnershipMode.ACTOR,
        ),
    )
    async def mutate():
        return {}

    matrix = build_route_policy_matrix(app.routes)
    assert matrix
    mutation = next(p for p in matrix if p.path == "/api/v1/items" and p.method == "POST")
    assert mutation.profile is ApiProfile.USER
    assert mutation.ownership is OwnershipMode.ACTOR
    validate_route_policy(app)


def test_registry_equals_manifest_and_rejects_any_other_tool(monkeypatch):
    monkeypatch.setattr("app.core.security.security_alerts.emit_security_alert", lambda *_, **__: True)
    register_production_tools()
    assert {item.name for item in action_registry.list_tools()} == {
        "recall_experiences",
        "recall_working_memory",
        "query_knowledge_graph",
        "find_related_concepts",
        "get_entity_details",
        "get_current_datetime",
        "render_ui_component",
    }

    @tool
    def unsafe_extra_tool() -> str:
        """Unapproved test tool."""
        return "no"

    with pytest.raises(PermissionError):
        action_registry.register(
            unsafe_extra_tool,
            category=ToolCategory.CUSTOM,
            permission_level=PermissionLevel.READ_ONLY,
            namespace="production",
        )


def test_autonomous_evolution_enable_flag_fails_closed(monkeypatch):
    app = FastAPI()
    monkeypatch.setattr("app.core.security.autonomy_guard.emit_security_alert", lambda *_, **__: True)
    monkeypatch.setenv("ENABLE_AUTO_EVOLUTION", "true")
    with pytest.raises(RuntimeError):
        validate_autonomous_evolution_disabled(app)


def test_security_webhook_is_signed_retried_and_outboxed(monkeypatch, tmp_path):
    calls = []

    class _Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def _urlopen(request, timeout):
        calls.append((request, timeout))
        if len(calls) < 3:
            raise OSError("temporary failure")
        return _Response()

    monkeypatch.setenv("SECURITY_ALERT_OUTBOX_PATH", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(settings, "SECURITY_ALERT_WEBHOOK_URL", "https://alerts.example/events")
    monkeypatch.setattr(settings, "SECURITY_ALERT_ALLOWED_HOSTS", ["alerts.example"])
    monkeypatch.setattr(
        settings,
        "SECURITY_ALERT_WEBHOOK_HMAC_KEY",
        "test-alert-key-with-at-least-thirty-two-bytes",
    )
    monkeypatch.setattr("app.core.security.security_alerts.urllib.request.urlopen", _urlopen)

    assert emit_security_alert("test_event", {"authorization": "Bearer sentinel-secret"})
    assert len(calls) == 3
    request = calls[-1][0]
    assert request.headers.get("X-janus-signature")
    assert b"sentinel-secret" not in request.data
    assert (tmp_path / "alerts.jsonl").is_file()


def test_recursive_redactor_removes_secret_pii_and_payment_values():
    sentinels = {
        "authorization": "Bearer secret-value",
        "nested": {
            "email": "person@example.com",
            "card": "4111 1111 1111 1111",
            "cvv": "123",
        },
    }
    rendered = repr(redact_sensitive_payload(sentinels))
    for original in ("secret-value", "person@example.com", "4111 1111 1111 1111", "123"):
        assert original not in rendered
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    assert REDACTION_FAILED in repr(redact_sensitive_payload(cyclic))


def test_log_and_audit_sinks_apply_the_same_fail_closed_redactor():
    sentinels = {
        "authorization": "Bearer sink-secret",
        "user_id": "actor-123",
        "email": "sink@example.com",
        "card": "4111 1111 1111 1111",
    }
    logging_output = repr(_redact_secrets(None, None, dict(sentinels)))
    ledger_output = repr(_normalize_ledger_payload({"details_json": sentinels}))
    for original in sentinels.values():
        assert original not in logging_output
        assert original not in ledger_output


def test_traces_and_metrics_never_emit_raw_actor_identifiers():
    root = Path(__file__).resolve().parents[1]
    trace_sources = (
        "backend/app/repositories/llm_repository.py",
        "backend/app/services/document_service.py",
        "backend/app/core/infrastructure/correlation_middleware.py",
        "backend/app/core/infrastructure/message_broker.py",
    )
    for relative in trace_sources:
        source = (root / relative).read_text(encoding="utf-8")
        assert 'set_attribute("janus.user_id", sid)' not in source
        assert 'set_attribute("janus.user_id", user_id)' not in source
    metric_sources = (
        "backend/app/core/monitoring/document_metrics.py",
        "backend/app/core/workers/google_productivity_worker.py",
        "backend/app/api/v1/endpoints/productivity.py",
        "backend/app/core/llm/pricing.py",
    )
    for relative in metric_sources:
        source = (root / relative).read_text(encoding="utf-8")
        assert ".labels(str(user_id)" not in source
        assert '.labels(actor, "' not in source


def test_removed_runtime_capabilities_are_not_reachable_from_production_sources():
    root = Path(__file__).resolve().parents[1]
    safe_source = (root / "backend/app/core/tools/safe_tools.py").read_text(encoding="utf-8")
    for forbidden in ("eval(", "exec(", "compile(", "subprocess", "python_sandbox"):
        assert forbidden not in safe_source
    router_source = (root / "backend/app/api/v1/router.py").read_text(encoding="utf-8")
    assert "sandbox.router" not in router_source
    assert "reflexion.router" not in router_source
    assert not (root / "backend/app/core/tools/faulty_tools.py").exists()
    assert not (root / "backend/app/core/evolution/evolution_manager.py").exists()
    removed_paths = (
        "backend/app/core/tools/command_sandbox.py",
        "backend/app/core/tools/external_cli_tools.py",
        "backend/app/core/tools/os_tools.py",
        "backend/app/core/workers/codex_worker.py",
        "backend/app/core/workers/code_agent_worker.py",
        "backend/app/core/workers/sandbox_agent_worker.py",
        "backend/app/core/evolution/evolution_sandbox.py",
    )
    assert all(not (root / relative).exists() for relative in removed_paths)
    registry_source = (root / "backend/app/core/tools/action_module.py").read_text(
        encoding="utf-8"
    )
    assert all(
        forbidden not in registry_source
        for forbidden in ("eval(", "exec(", "subprocess", "python_sandbox")
    )
    self_study_source = (root / "backend/app/services/autonomy_admin_service.py").read_text(
        encoding="utf-8"
    )
    assert "import subprocess" not in self_study_source
    assert "subprocess.run" not in self_study_source


def test_sensitive_autonomy_service_methods_require_internal_actor_authorization():
    source = (
        Path(__file__).resolve().parents[1]
        / "backend/app/services/autonomy_service.py"
    ).read_text(encoding="utf-8")
    for signature in (
        "async def start(self, config: AutonomyConfig, *, actor: ActorContext)",
        "async def stop(self, *, actor: ActorContext)",
        "def reset_throttle(self, *, actor: ActorContext)",
        "def update_plan(self, plan: list[dict[str, Any]], *, actor: ActorContext)",
    ):
        assert signature in source


def test_frontend_transport_never_sets_identity_headers():
    root = Path(__file__).resolve().parents[1]
    sources = [
        root / "frontend/src/app/services/api-context.service.ts",
        root / "frontend/src/app/services/chat-auth-headers.util.ts",
    ]
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    for forbidden in ("X-User-Id", "X-Actor-User-Id", "X-Project-Id"):
        assert forbidden not in rendered
