import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))  # noqa: E402
from app.services.observability_service import ObservabilityService  # noqa: E402


class DummyRepo:
    def __init__(self, events):
        self._events = events

    def get_audit_events_by_trace_id(self, trace_id: str, limit: int = 2000, offset: int = 0):
        assert trace_id == "req-1"
        assert limit == 2000
        assert offset == 0
        return self._events


def test_get_request_pipeline_dashboard_aggregates_pipeline():
    repo = DummyRepo(
        events=[
            {
                "id": 2,
                "endpoint": "tool_executor",
                "action": "tool_done",
                "tool": "list_directory",
                "status": "ok",
                "latency_ms": 120,
                "trace_id": "req-1",
                "created_at": 100.1,
                "details_json": '{"stage":"tool_execution","source":"tool"}',
            },
            {
                "id": 1,
                "endpoint": "chat",
                "action": "llm_start",
                "tool": "openai",
                "status": "ok",
                "latency_ms": 15,
                "trace_id": "req-1",
                "created_at": 100.0,
                "details_json": {"stage": "llm_request"},
            },
            {
                "id": 3,
                "endpoint": "chat",
                "action": "llm_error",
                "tool": "openai",
                "status": "error",
                "latency_ms": 30,
                "trace_id": "req-1",
                "created_at": 100.3,
                "details_json": "non-json-payload",
            },
        ]
    )
    service = ObservabilityService(repo)

    dashboard = service.get_request_pipeline_dashboard("req-1", include_details=True)

    assert dashboard["request_id"] == "req-1"
    assert dashboard["found"] is True
    assert dashboard["summary"]["total_events"] == 3
    assert dashboard["summary"]["duration_ms"] == 300
    assert dashboard["summary"]["status_counts"] == {"error": 1, "ok": 2}
    assert dashboard["summary"]["endpoint_counts"] == {"chat": 2, "tool_executor": 1}
    assert dashboard["summary"]["action_counts"] == {"llm_error": 1, "llm_start": 1, "tool_done": 1}
    assert dashboard["summary"]["tool_counts"] == {"list_directory": 1, "openai": 2}
    assert [item["id"] for item in dashboard["timeline"]] == [1, 2, 3]
    assert dashboard["timeline"][0]["offset_ms"] == 0
    assert dashboard["timeline"][0]["stage"] == "llm_request"
    assert dashboard["timeline"][1]["offset_ms"] == 100
    assert dashboard["timeline"][1]["stage"] == "tool_execution"
    assert dashboard["timeline"][2]["offset_ms"] == 300
    assert dashboard["timeline"][2]["details"] == {"raw": "non-json-payload"}


def test_get_request_pipeline_dashboard_returns_not_found_payload():
    service = ObservabilityService(DummyRepo(events=[]))

    dashboard = service.get_request_pipeline_dashboard("req-1")

    assert dashboard["request_id"] == "req-1"
    assert dashboard["found"] is False
    assert dashboard["summary"]["total_events"] == 0
    assert dashboard["timeline"] == []
