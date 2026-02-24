import pytest

from app.services.observability_service import (
    ObservabilityService,
    ObservabilityServiceError,
    observe_ux_metric_record,
)
from app.repositories.observability_repository import ObservabilityRepositoryError


class _FakeMetricChild:
    def __init__(self, parent, labels):
        self._parent = parent
        self._labels = labels

    def inc(self, amount: float = 1.0):
        self._parent.calls.append(("inc", self._labels, amount))

    def observe(self, value: float):
        self._parent.calls.append(("observe", self._labels, value))


class _FakeMetric:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, object], float]] = []

    def labels(self, **labels):
        return _FakeMetricChild(self, labels)


@pytest.fixture()
def fake_metrics(monkeypatch):
    import app.services.observability_service as obs_module

    ops_total = _FakeMetric()
    duration = _FakeMetric()
    result_items = _FakeMetric()
    ux_total = _FakeMetric()
    ux_latency = _FakeMetric()
    monkeypatch.setattr(obs_module, "_OBS_OPERATIONS_TOTAL", ops_total)
    monkeypatch.setattr(obs_module, "_OBS_OPERATION_DURATION_SECONDS", duration)
    monkeypatch.setattr(obs_module, "_OBS_RESULT_ITEMS", result_items)
    monkeypatch.setattr(obs_module, "_OBS_UX_METRICS_TOTAL", ux_total)
    monkeypatch.setattr(obs_module, "_OBS_UX_LATENCY_SECONDS", ux_latency)
    return obs_module, ops_total, duration, result_items, ux_total, ux_latency


def _events_for_dashboard():
    return [
        {
            "id": 1,
            "endpoint": "chat",
            "action": "start",
            "tool": "openai",
            "status": "ok",
            "latency_ms": 10,
            "trace_id": "req-1",
            "created_at": 100.0,
            "details_json": '{"stage":"llm_request"}',
        },
        {
            "id": 2,
            "endpoint": "tool_executor",
            "action": "tool_done",
            "tool": "list_directory",
            "status": "ok",
            "latency_ms": 50,
            "trace_id": "req-1",
            "created_at": 100.2,
            "details_json": '{"stage":"tool_execution"}',
        },
    ]


@pytest.mark.asyncio
async def test_domain_slo_report_records_metrics_success(fake_metrics):
    _obs_module, ops_total, duration, result_items, *_ = fake_metrics

    class _Repo:
        def get_audit_events(self, **_kwargs):
            return [
                {"endpoint": "/api/v1/chat/message", "status": "ok", "latency_ms": 120},
                {"endpoint": "/api/v1/chat/message", "status": "ok", "latency_ms": 130},
                {"endpoint": "/api/v1/chat/message", "status": "ok", "latency_ms": 150},
            ]

    service = ObservabilityService(repo=_Repo())
    report = await service.get_domain_slo_report(window_minutes=10, min_events=2)

    assert report["status"] in {"ok", "degraded", "insufficient_data"}
    assert any(
        call[0] == "inc"
        and call[1].get("operation") == "domain_slo_report"
        and call[1].get("outcome") == "success"
        for call in ops_total.calls
    )
    assert any(
        call[0] == "observe" and call[1].get("operation") == "domain_slo_report"
        for call in duration.calls
    )
    kinds = {call[1].get("kind") for call in result_items.calls if call[1].get("operation") == "domain_slo_report"}
    assert {"domains", "alerts", "events"}.issubset(kinds)


@pytest.mark.asyncio
async def test_domain_slo_report_records_metrics_error_and_raises(fake_metrics):
    _obs_module, ops_total, duration, result_items, *_ = fake_metrics

    class _Repo:
        def get_audit_events(self, **_kwargs):
            raise ObservabilityRepositoryError("boom")

    service = ObservabilityService(repo=_Repo())
    with pytest.raises(ObservabilityServiceError):
        await service.get_domain_slo_report(window_minutes=10, min_events=2)

    assert any(
        call[0] == "inc"
        and call[1].get("operation") == "domain_slo_report"
        and call[1].get("outcome") == "error"
        for call in ops_total.calls
    )
    assert any(
        call[0] == "observe" and call[1].get("operation") == "domain_slo_report"
        for call in duration.calls
    )
    assert not result_items.calls


def test_request_pipeline_dashboard_records_timeline_metric(fake_metrics):
    _obs_module, ops_total, duration, result_items, *_ = fake_metrics

    class _Repo:
        def get_audit_events_by_trace_id(self, trace_id: str, limit: int = 2000, offset: int = 0):
            assert trace_id == "req-1"
            return _events_for_dashboard()

    service = ObservabilityService(repo=_Repo())
    dashboard = service.get_request_pipeline_dashboard("req-1", include_details=True)

    assert dashboard["found"] is True
    assert dashboard["summary"]["total_events"] == 2
    assert any(
        call[0] == "inc"
        and call[1].get("operation") == "request_pipeline_dashboard"
        and call[1].get("outcome") == "success"
        for call in ops_total.calls
    )
    assert any(
        call[0] == "observe"
        and call[1].get("operation") == "request_pipeline_dashboard"
        and call[1].get("kind") == "timeline"
        for call in result_items.calls
    )
    assert any(
        call[0] == "observe" and call[1].get("operation") == "request_pipeline_dashboard"
        for call in duration.calls
    )


def test_observe_ux_metric_record_tracks_low_cardinality_metrics(fake_metrics):
    _obs_module, _ops_total, _duration, _result_items, ux_total, ux_latency = fake_metrics

    observe_ux_metric_record(
        outcome="OK",
        provider="  OpenAI  ",
        ttft_ms=120.0,
        latency_ms=850.0,
    )

    assert any(
        call[0] == "inc"
        and call[1].get("outcome") == "ok"
        and call[1].get("provider") == "openai"
        for call in ux_total.calls
    )
    metrics = {call[1].get("metric") for call in ux_latency.calls if call[0] == "observe"}
    assert {"ttft", "latency"} == metrics
