from __future__ import annotations

import pytest

from app.config import settings
from app.repositories.audit_ledger_repository import AuditLedgerRepository, AuditLedgerWriteError


def test_append_raises_when_enabled_ledger_cannot_open_session(monkeypatch):
    monkeypatch.setattr(settings, "AUDIT_LEDGER_ENABLED", True)
    repository = AuditLedgerRepository()

    def _fail_session():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(repository, "_get_session", _fail_session)

    with pytest.raises(AuditLedgerWriteError, match="Failed to append"):
        repository.append(
            actor_user_id=1,
            endpoint="test",
            action="write",
            tool=None,
            status="ok",
            trace_id="trace-1",
            payload_json={},
        )


def test_append_returns_none_only_when_ledger_is_explicitly_disabled(monkeypatch):
    monkeypatch.setattr(settings, "AUDIT_LEDGER_ENABLED", False)
    repository = AuditLedgerRepository()
    monkeypatch.setattr(
        repository,
        "_get_session",
        lambda: pytest.fail("disabled ledger must not open a database session"),
    )

    assert (
        repository.append(
            actor_user_id=None,
            endpoint="test",
            action="disabled",
            tool=None,
            status="skipped",
            trace_id=None,
            payload_json=None,
        )
        is None
    )
