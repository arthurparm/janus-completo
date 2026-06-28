import asyncio

import pytest
from app.core.monitoring import auto_healer


class FakeCounter:
    def __init__(self):
        self.increments = []

    def labels(self, **labels):
        self.increments.append(labels)
        return self

    def inc(self):
        self.increments.append("inc")


@pytest.mark.asyncio
async def test_run_healing_step_logs_failure_without_raising(monkeypatch):
    errors = []
    attempts = FakeCounter()
    successes = FakeCounter()
    failures = FakeCounter()

    def capture_error(event, **kwargs):
        errors.append((event, kwargs))

    async def failing_step():
        raise RuntimeError("broker reconnect failed")

    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_ATTEMPTS", attempts)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_SUCCESSES", successes)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_FAILURES", failures)
    monkeypatch.setattr(auto_healer.logger, "error", capture_error)

    await auto_healer._run_healing_step("message_broker", failing_step)

    assert attempts.increments == [{"step": "message_broker"}, "inc"]
    assert successes.increments == []
    assert failures.increments == [{"step": "message_broker"}, "inc"]
    assert errors == [
        (
            "auto_healer_step_failed",
            {
                "step": "message_broker",
                "error": "broker reconnect failed",
                "message": None,
                "exc_info": True,
            },
        )
    ]


@pytest.mark.asyncio
async def test_run_healing_step_records_success(monkeypatch):
    attempts = FakeCounter()
    successes = FakeCounter()
    failures = FakeCounter()
    calls = []

    async def successful_step():
        calls.append("called")

    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_ATTEMPTS", attempts)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_SUCCESSES", successes)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_FAILURES", failures)

    await auto_healer._run_healing_step("llm_router", successful_step)

    assert calls == ["called"]
    assert attempts.increments == [{"step": "llm_router"}, "inc"]
    assert successes.increments == [{"step": "llm_router"}, "inc"]
    assert failures.increments == []


@pytest.mark.asyncio
async def test_run_healing_step_does_not_mark_success_after_internal_failure(monkeypatch):
    attempts = FakeCounter()
    successes = FakeCounter()
    failures = FakeCounter()
    errors = []

    async def partially_failing_step():
        auto_healer._record_healing_failure(
            "message_broker",
            RuntimeError("internal reconnect failed"),
            "internal failure",
        )

    def capture_error(event, **kwargs):
        errors.append((event, kwargs))

    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_ATTEMPTS", attempts)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_SUCCESSES", successes)
    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_FAILURES", failures)
    monkeypatch.setattr(auto_healer.logger, "error", capture_error)
    auto_healer._healing_failure_counts.clear()

    await auto_healer._run_healing_step("message_broker", partially_failing_step)

    assert attempts.increments == [{"step": "message_broker"}, "inc"]
    assert failures.increments == [{"step": "message_broker"}, "inc"]
    assert successes.increments == []
    assert auto_healer._healing_failure_counts["message_broker"] == 1
    assert errors[0][0] == "auto_healer_step_failed"


@pytest.mark.asyncio
async def test_internal_healing_failure_increments_metric(monkeypatch):
    errors = []
    counter = FakeCounter()

    async def failing_get_broker():
        raise RuntimeError("broker factory failed")

    def capture_error(event, **kwargs):
        errors.append((event, kwargs))

    monkeypatch.setattr(auto_healer, "AUTO_HEALER_STEP_FAILURES", counter)
    monkeypatch.setattr(auto_healer, "get_broker", failing_get_broker)
    monkeypatch.setattr(auto_healer.logger, "error", capture_error)

    await auto_healer._heal_message_broker()

    assert counter.increments == [{"step": "message_broker"}, "inc"]
    assert errors[0][0] == "auto_healer_step_failed"
    assert errors[0][1]["step"] == "message_broker"
    assert errors[0][1]["error"] == "broker factory failed"
    assert "falha ao reconectar broker" in errors[0][1]["message"]


@pytest.mark.asyncio
async def test_start_auto_healer_is_idempotent_for_running_task(monkeypatch):
    original_task = auto_healer._healer_task
    auto_healer._healer_task = None

    class DummyMonitor:
        last_results = {}

        async def check_all_components(self):
            return {}

        def get_system_health(self):
            return {"status": "healthy", "score": 100}

    async def noop(_system=None):
        return None

    monkeypatch.setattr(auto_healer, "get_health_monitor", lambda: DummyMonitor())
    monkeypatch.setattr(auto_healer, "_heal_llm_router", noop)
    monkeypatch.setattr(auto_healer, "_maybe_trigger_meta_agent", noop)
    monkeypatch.setattr(auto_healer, "_heal_with_codex", noop)

    task1 = await auto_healer.start_auto_healer(interval_seconds=3600)
    task2 = await auto_healer.start_auto_healer(interval_seconds=1)

    try:
        assert task1 is task2
        assert not task1.done()
    finally:
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass
        auto_healer._healer_task = original_task
