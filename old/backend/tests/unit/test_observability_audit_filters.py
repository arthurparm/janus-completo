from typing import Any

import pytest

import app.repositories.observability_repository as repository_module
from app.repositories.observability_repository import ObservabilityRepository


class _Query:
    def __init__(self) -> None:
        self.filters: list[tuple[str, Any]] = []

    def filter(self, expression: Any) -> "_Query":
        self.filters.append((str(expression.left.key), expression.right.value))
        return self

    def order_by(self, _expression: Any) -> "_Query":
        return self

    def offset(self, _offset: int) -> "_Query":
        return self

    def limit(self, _limit: int) -> "_Query":
        return self

    def all(self) -> list[Any]:
        return []

    def count(self) -> int:
        return 0


class _Session:
    def __init__(self) -> None:
        self.queries: list[_Query] = []

    def query(self, _model: Any) -> _Query:
        query = _Query()
        self.queries.append(query)
        return query

    def close(self) -> None:
        return None


def test_audit_page_and_count_apply_endpoint_and_action_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    database = getattr(repository_module, "db")
    monkeypatch.setattr(database, "get_session_direct", lambda: session)
    repository = ObservabilityRepository(object(), object())

    events = repository.get_audit_events(
        user_id=None,
        tool=None,
        status="planned",
        start_ts=None,
        end_ts=None,
        endpoint="optimization_continuous",
        action="continuous_cycle_completed",
    )
    total = repository.get_audit_events_count(
        user_id=None,
        tool=None,
        status="planned",
        start_ts=None,
        end_ts=None,
        endpoint="optimization_continuous",
        action="continuous_cycle_completed",
    )

    expected_filters = {
        ("status", "planned"),
        ("endpoint", "optimization_continuous"),
        ("action", "continuous_cycle_completed"),
    }
    assert events == []
    assert total == 0
    assert set(session.queries[0].filters) == expected_filters
    assert set(session.queries[1].filters) == expected_filters
