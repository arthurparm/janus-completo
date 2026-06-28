import pytest

from app.core.autonomy.domain_circuit_breaker import DomainCircuitBreaker


@pytest.fixture
def cb():
    return DomainCircuitBreaker(failure_threshold=3, recovery_timeout=300.0)


class TestCircuitBreaker:

    def test_opens_after_three_failures(self, cb):
        cb.record_failure("tools")
        assert cb.is_open("tools") is False
        cb.record_failure("tools")
        assert cb.is_open("tools") is False
        cb.record_failure("tools")
        assert cb.is_open("tools") is True

    def test_stays_closed_below_threshold(self, cb):
        cb.record_failure("code")
        cb.record_failure("code")
        assert cb.is_open("code") is False

    def test_record_success_resets(self, cb):
        cb.record_failure("tools")
        cb.record_failure("tools")
        cb.record_failure("tools")
        assert cb.is_open("tools") is True
        cb.record_success("tools")
        assert cb.is_open("tools") is False

    def test_different_domains_independent(self, cb):
        cb.record_failure("tools")
        cb.record_failure("tools")
        cb.record_failure("tools")
        assert cb.is_open("tools") is True
        assert cb.is_open("code") is False

    def test_recovery_after_timeout(self, cb, monkeypatch):
        cb.record_failure("knowledge")
        cb.record_failure("knowledge")
        cb.record_failure("knowledge")
        assert cb.is_open("knowledge") is True

        import time
        fake_now = time.time() + 301.0
        monkeypatch.setattr(time, "time", lambda: fake_now)
        assert cb.is_open("knowledge") is False

    def test_get_domain_health_returns_all(self, cb):
        cb.record_failure("tools")
        cb.is_open("code")
        cb.is_open("knowledge")
        cb.is_open("deployment")
        health = cb.get_domain_health()
        assert "code" in health
        assert "knowledge" in health
        assert "tools" in health
        assert "deployment" in health
        assert health["tools"]["failure_count"] == 1
        assert health["tools"]["is_open"] is False
