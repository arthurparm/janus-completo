from datetime import datetime

from app.core.infrastructure.resilience import CircuitBreaker, CircuitBreakerState
from app.core.llm import resilience
from app.core.llm.types import CachedLLM


def test_llm_pool_snapshot_and_summary_are_serializable_and_defensive(monkeypatch):
    created_at = datetime.utcnow()
    monkeypatch.setattr(
        resilience,
        "_llm_pool",
        {
            "openai:gpt-4o-mini": [
                CachedLLM(
                    instance=object(),
                    created_at=created_at,
                    provider="openai",
                    model="gpt-4o-mini",
                    consecutive_failures=2,
                )
            ]
        },
    )

    snapshot = resilience.get_llm_pool_snapshot()
    summary = resilience.get_llm_pool_summary()

    assert summary == {"pool_keys": 1, "pool_total_instances": 1}
    assert "openai:gpt-4o-mini" in snapshot
    item = snapshot["openai:gpt-4o-mini"][0]
    assert item["provider"] == "openai"
    assert item["model"] == "gpt-4o-mini"
    assert item["consecutive_failures"] == 2
    assert item["created_at"] == created_at.isoformat()
    assert "instance" not in item


def test_circuit_breaker_snapshot_and_reset_provider(monkeypatch):
    cb = CircuitBreaker()
    cb.state = CircuitBreakerState.OPEN
    cb.failure_count = 3
    cb.last_failure_time = 123.45
    monkeypatch.setattr(resilience, "_provider_circuit_breakers", {"openai": cb})

    snapshot = resilience.get_circuit_breaker_snapshot()
    assert snapshot["openai"]["state"] == "OPEN"
    assert snapshot["openai"]["failure_count"] == 3
    assert snapshot["openai"]["last_failure_time"] == 123.45

    assert resilience.reset_provider_circuit_breaker("missing") is False
    assert resilience.reset_provider_circuit_breaker("openai") is True
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_force_reset_stale_open_circuit_breakers_resets_only_eligible(monkeypatch):
    now = 1_000.0
    stale = CircuitBreaker()
    stale.state = CircuitBreakerState.OPEN
    stale.last_failure_time = now - 500
    stale.failure_count = 7

    fresh = CircuitBreaker()
    fresh.state = CircuitBreakerState.OPEN
    fresh.last_failure_time = now - 5
    fresh.failure_count = 4

    no_timestamp = CircuitBreaker()
    no_timestamp.state = CircuitBreakerState.OPEN
    no_timestamp.last_failure_time = None
    no_timestamp.failure_count = 2

    closed = CircuitBreaker()
    closed.state = CircuitBreakerState.CLOSED

    monkeypatch.setattr(
        resilience,
        "_provider_circuit_breakers",
        {
            "stale": stale,
            "fresh": fresh,
            "no_ts": no_timestamp,
            "closed": closed,
        },
    )
    monkeypatch.setattr(resilience.time, "time", lambda: now)

    reset = resilience.force_reset_stale_open_circuit_breakers(60.0)

    assert set(reset) == {"stale", "no_ts"}
    assert stale.state == CircuitBreakerState.CLOSED
    assert no_timestamp.state == CircuitBreakerState.CLOSED
    assert fresh.state == CircuitBreakerState.OPEN
    assert closed.state == CircuitBreakerState.CLOSED
