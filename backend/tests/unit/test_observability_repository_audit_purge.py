from __future__ import annotations

import pytest

import app.repositories.observability_repository as repo_module
from app.repositories.observability_repository import ObservabilityRepository, ObservabilityRepositoryError


class _DummyMonitor:
    pass


class _DummyPoisonPillHandler:
    pass


class _FakeQuery:
    def __init__(self, removed: int):
        self.removed = removed
        self.filtered = False

    def filter(self, *_args, **_kwargs):
        self.filtered = True
        return self

    def delete(self, synchronize_session: bool = False):
        assert synchronize_session is False
        return self.removed


class _FakeSession:
    def __init__(self, removed: int):
        self.query_obj = _FakeQuery(removed)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def query(self, _model):
        return self.query_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_purge_old_audit_events_is_rejected():
    repo = ObservabilityRepository(_DummyMonitor(), _DummyPoisonPillHandler())
    with pytest.raises(ObservabilityRepositoryError):
        repo.purge_old_audit_events(30)
