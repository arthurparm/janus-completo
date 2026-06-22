from app.config import settings
from app.core.security import egress_policy


def test_enforce_worker_http_egress_allows_internal_defaults(monkeypatch):
    monkeypatch.setattr(settings, "WORKER_EGRESS_ALLOW_HOSTS", [])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)

    assert (
        egress_policy.enforce_worker_http_egress(
            "http://rabbitmq:15672/api/health", tool="rabbitmq_management"
        )
        is not None
    )


def test_enforce_worker_http_egress_denies_unknown_host(monkeypatch):
    monkeypatch.setattr(settings, "WORKER_EGRESS_ALLOW_HOSTS", [])
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)
    monkeypatch.setattr(settings, "XAI_API_KEY", None)
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)

    assert (
        egress_policy.enforce_worker_http_egress(
            "https://evil.example.com/x", tool="worker_test"
        )
        is None
    )


def test_enforce_worker_http_egress_allows_google_when_oauth_configured(monkeypatch):
    monkeypatch.setattr(settings, "WORKER_EGRESS_ALLOW_HOSTS", [])
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "dummy")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "dummy")
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)

    assert (
        egress_policy.enforce_worker_http_egress(
            "https://oauth2.googleapis.com/token", tool="google_productivity_worker"
        )
        is not None
    )

