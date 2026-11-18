from __future__ import annotations

import pytest

import app.repositories.audit_ledger_repository as ledger_module
from app.repositories.observability_repository import (
    ObservabilityRepositoryError,
    record_audit_event_direct,
)


def test_direct_audit_returns_true_when_event_is_persisted(monkeypatch):
    monkeypatch.setattr(ledger_module.audit_ledger_repository, "append", lambda **_kwargs: 17)

    assert record_audit_event_direct(endpoint="test", action="ok", status="success") is True


@pytest.mark.parametrize("append_result", [None, RuntimeError("database unavailable")])
def test_direct_audit_reports_best_effort_failure(monkeypatch, append_result):
    def _append(**_kwargs):
        if isinstance(append_result, Exception):
            raise append_result
        return append_result

    monkeypatch.setattr(ledger_module.audit_ledger_repository, "append", _append)

    assert record_audit_event_direct(endpoint="test", action="failed", status="error") is False


@pytest.mark.parametrize("append_result", [None, RuntimeError("database unavailable")])
def test_direct_audit_required_mode_raises(monkeypatch, append_result):
    def _append(**_kwargs):
        if isinstance(append_result, Exception):
            raise append_result
        return append_result

    monkeypatch.setattr(ledger_module.audit_ledger_repository, "append", _append)

    with pytest.raises(ObservabilityRepositoryError):
        record_audit_event_direct(
            endpoint="test",
            action="required",
            status="error",
            required=True,
        )
