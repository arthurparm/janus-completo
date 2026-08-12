from __future__ import annotations

import json

import app.repositories.observability_repository as observability_module
from app.core.security.actor_context import ActorContext, AuthMethod
from app.core.security.security_audit import record_security_denial, record_security_event


def test_security_event_uses_outbox_when_primary_sink_returns_false(monkeypatch, tmp_path):
    outbox = tmp_path / "security-audit.jsonl"
    monkeypatch.setenv("SECURITY_AUDIT_OUTBOX_PATH", str(outbox))
    monkeypatch.setattr(observability_module, "record_audit_event_direct", lambda **_kwargs: False)

    assert (
        record_security_event(
            endpoint="egress_policy",
            action="egress_blocked",
            status="blocked",
            event={"reason": "unsafe_url", "token": "must-not-leak"},
        )
        is True
    )

    persisted = json.loads(outbox.read_text(encoding="utf-8"))
    assert persisted["reason"] == "unsafe_url"
    assert persisted["token"] != "must-not-leak"


def test_security_denial_hashes_actor_and_spools_on_primary_failure(monkeypatch, tmp_path):
    outbox = tmp_path / "security-audit.jsonl"
    monkeypatch.setenv("SECURITY_AUDIT_OUTBOX_PATH", str(outbox))
    monkeypatch.setattr(observability_module, "record_audit_event_direct", lambda **_kwargs: False)
    actor = ActorContext.authenticated(
        actor_id="private-actor-id",
        roles=("USER",),
        auth_method=AuthMethod.OIDC,
        trace_id="trace-1",
    )

    record_security_denial(
        method="GET",
        route="/api/private",
        reason="missing_scope",
        trace_id="trace-1",
        actor=actor,
        status_code=403,
    )

    raw = outbox.read_text(encoding="utf-8")
    persisted = json.loads(raw)
    assert persisted["actor_reference"].startswith("actor:")
    assert "private-actor-id" not in raw


def test_security_event_does_not_spool_after_primary_success(monkeypatch, tmp_path):
    outbox = tmp_path / "security-audit.jsonl"
    monkeypatch.setenv("SECURITY_AUDIT_OUTBOX_PATH", str(outbox))
    monkeypatch.setattr(observability_module, "record_audit_event_direct", lambda **_kwargs: True)

    assert (
        record_security_event(
            endpoint="test",
            action="blocked",
            status="blocked",
            event={"reason": "policy"},
        )
        is True
    )
    assert not outbox.exists()
