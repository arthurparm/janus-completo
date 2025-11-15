import json
from types import SimpleNamespace

from app.repositories.observability_repository import ObservabilityRepository


class DummyMonitor:
    def check(self):
        return True


class DummyPPHandler:
    def get_failure_stats(self, queue=None):
        return {}


def test_export_sanitize_redacts_sensitive_fields(monkeypatch):
    repo = ObservabilityRepository(DummyMonitor(), DummyPPHandler())

    rows = [
        {
            "id": 1,
            "user_id": 123,
            "endpoint": "/api/v1/observability/hitl/action",
            "action": "promote",
            "tool": "hitl",
            "status": "ok",
            "latency_ms": 10,
            "trace_id": "abc",
            "details_json": json.dumps({"email": "user@example.com", "token": "secret", "note": "ok"}),
            "created_at": 1730000000,
        }
    ]

    monkeypatch.setattr(repo, "get_audit_events", lambda **kwargs: rows)

    text = repo.export_audit_events_json(sanitize=True)
    data = json.loads(text)
    assert "events" in data
    ev = data["events"][0]
    dj = json.loads(ev["details_json"]) if ev.get("details_json") else {}
    assert dj.get("email") == "[REDACTED]"
    assert dj.get("token") == "[REDACTED]"
    assert dj.get("note") == "ok"