import pytest

from app.config import settings
from app.core.monitoring.domain_slo_metrics import derive_domain_from_path
from app.services.observability_service import ObservabilityService


def _event(endpoint: str, *, status: str = "ok", latency_ms: float = 120.0) -> dict:
    return {
        "endpoint": endpoint,
        "status": status,
        "latency_ms": latency_ms,
    }


@pytest.mark.asyncio
async def test_oq002_domain_slo_report_flags_chat_breach(monkeypatch):
    monkeypatch.setattr(settings, "OQ_SLO_CHAT_MAX_ERROR_RATE_PCT", 5.0)
    monkeypatch.setattr(settings, "OQ_SLO_CHAT_MAX_P95_LATENCY_MS", 800.0)
    monkeypatch.setattr(settings, "OQ_SLO_MIN_EVENTS_PER_DOMAIN", 3)

    events = [
        _event("/api/v1/chat/message", status="ok", latency_ms=100),
        _event("/api/v1/chat/message", status="ok", latency_ms=120),
        _event("/api/v1/chat/message", status="error", latency_ms=1500),
        _event("/api/v1/chat/message", status="error", latency_ms=1400),
        _event("/api/v1/rag/search", status="ok", latency_ms=180),
        _event("/api/v1/rag/search", status="ok", latency_ms=220),
        _event("/api/v1/rag/search", status="ok", latency_ms=260),
        _event("/api/v1/tools/", status="ok", latency_ms=90),
        _event("/api/v1/tools/stats/usage", status="ok", latency_ms=110),
        _event("/api/v1/tools/categories/list", status="ok", latency_ms=130),
    ]

    class _Repo:
        def get_audit_events(self, **_kwargs):
            return events

    report = await ObservabilityService(repo=_Repo()).get_domain_slo_report(
        window_minutes=10,
        min_events=3,
    )

    assert report["status"] == "degraded"
    assert len(report["active_alerts"]) >= 1
    chat = next(item for item in report["domains"] if item["domain"] == "chat")
    assert chat["status"] == "breach"
    breach_types = {b["type"] for b in chat["breaches"]}
    assert "error_rate" in breach_types
    assert "latency_p95_ms" in breach_types


@pytest.mark.asyncio
async def test_oq002_domain_slo_report_insufficient_data():
    class _Repo:
        def get_audit_events(self, **_kwargs):
            return []

    report = await ObservabilityService(repo=_Repo()).get_domain_slo_report(
        window_minutes=5,
        min_events=2,
    )

    assert report["status"] == "insufficient_data"
    assert report["active_alerts"] == []
    assert all(item["status"] == "insufficient_data" for item in report["domains"])


def test_oq002_domain_path_mapping():
    assert derive_domain_from_path("/api/v1/chat/message") == "chat"
    assert derive_domain_from_path("/api/v1/rag/search") == "rag"
    assert derive_domain_from_path("/api/v1/tools/stats/usage") == "tools"
    assert derive_domain_from_path("/api/v1/workers/status") == "workers"
    assert derive_domain_from_path("/health") == "other"
