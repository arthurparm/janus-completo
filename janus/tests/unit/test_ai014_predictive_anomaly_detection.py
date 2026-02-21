import pytest

from app.config import settings
from app.services.observability_service import ObservabilityService
from app.services.predictive_anomaly_detection_service import PredictiveAnomalyDetectionService


def _build_events(*, start_ts: float, end_ts: float, count: int, spike_last: int = 0):
    events = []
    step = (end_ts - start_ts) / max(1, count)
    for i in range(count):
        ts = start_ts + (i * step)
        is_spike = i >= (count - spike_last)
        events.append(
            {
                "created_at": ts,
                "latency_ms": 900 if is_spike else 120,
                "status": "error" if is_spike else "ok",
            }
        )
    return events


def test_ai014_detector_flags_latency_error_and_backlog_anomaly(monkeypatch):
    monkeypatch.setattr(settings, "AI_ANOMALY_ZSCORE_THRESHOLD", 2.0)
    monkeypatch.setattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 100)

    svc = PredictiveAnomalyDetectionService()
    start_ts = 1_700_000_000.0
    end_ts = start_ts + (6 * 3600)
    events = _build_events(start_ts=start_ts, end_ts=end_ts, count=240, spike_last=30)
    queues = [
        {"name": "janus.agent.tasks", "messages": 180, "consumers": 1},
        {"name": "janus.knowledge.consolidation", "messages": 80, "consumers": 0},
    ]

    report = svc.analyze(
        events=events,
        queue_snapshots=queues,
        start_ts=start_ts,
        end_ts=end_ts,
        bucket_minutes=10,
        min_events=20,
    )

    assert report["status"] == "ok"
    metrics = {item["metric"] for item in report["anomalies"]}
    assert "latency_p95_ms" in metrics
    assert "error_rate" in metrics
    assert "queue_backlog_total" in metrics
    assert report["risk"]["should_alert"] is True
    assert report["risk"]["level"] in {"medium", "high"}


def test_ai014_detector_returns_insufficient_data_when_volume_is_low():
    svc = PredictiveAnomalyDetectionService()
    start_ts = 1_700_000_000.0
    end_ts = start_ts + 3600
    events = _build_events(start_ts=start_ts, end_ts=end_ts, count=4, spike_last=0)

    report = svc.analyze(
        events=events,
        queue_snapshots=[],
        start_ts=start_ts,
        end_ts=end_ts,
        bucket_minutes=10,
        min_events=20,
    )

    assert report["status"] == "insufficient_data"
    assert report["risk"]["level"] == "low"


@pytest.mark.asyncio
async def test_ai014_observability_service_integrates_detector_and_broker(monkeypatch):
    monkeypatch.setattr(settings, "AI_ANOMALY_DETECTION_ENABLED", True)
    monkeypatch.setattr(settings, "AI_ANOMALY_WINDOW_HOURS", 1)
    monkeypatch.setattr(settings, "AI_ANOMALY_BUCKET_MINUTES", 10)
    monkeypatch.setattr(settings, "AI_ANOMALY_MIN_EVENTS", 5)
    monkeypatch.setattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 50)
    monkeypatch.setattr(
        settings,
        "AI_ANOMALY_QUEUE_NAMES",
        ["janus.agent.tasks", "janus.knowledge.consolidation"],
    )

    now_ts = 1_700_100_000.0

    class _FakeRepo:
        def get_audit_events(self, **_kwargs):
            return _build_events(
                start_ts=now_ts - 3600,
                end_ts=now_ts,
                count=80,
                spike_last=10,
            )

    class _FakeBroker:
        async def get_queue_info(self, queue_name: str):
            if queue_name == "janus.agent.tasks":
                return {"name": queue_name, "messages": 90, "consumers": 1}
            return {"name": queue_name, "messages": 10, "consumers": 1}

    async def _fake_get_broker():
        return _FakeBroker()

    import app.services.observability_service as obs_module
    import app.core.infrastructure.message_broker as broker_module

    monkeypatch.setattr(obs_module.time, "time", lambda: now_ts)
    monkeypatch.setattr(broker_module, "get_broker", _fake_get_broker)

    service = ObservabilityService(repo=_FakeRepo())
    report = await service.get_predictive_anomaly_report()

    assert report["status"] in {"ok", "insufficient_data"}
    assert "risk" in report
    assert "anomalies" in report

