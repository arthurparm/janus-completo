from app.config import settings
from app.core.security import egress_policy
from app.core.security.url_safety import SafeHttpTarget


def test_enforce_tool_http_egress_denies_when_allowlist_empty(monkeypatch):
    monkeypatch.setattr(settings, "TOOL_EGRESS_ALLOW_HOSTS", [])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)

    assert egress_policy.enforce_tool_http_egress("https://example.com/a", tool="browse_url") is None


def test_enforce_tool_http_egress_denies_when_host_not_allowlisted(monkeypatch):
    monkeypatch.setattr(settings, "TOOL_EGRESS_ALLOW_HOSTS", ["allowed.example"])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)
    monkeypatch.setattr(egress_policy, "is_allowlisted_host", lambda raw_url, allowed_hosts: False)

    assert egress_policy.enforce_tool_http_egress("https://example.com/a", tool="browse_url") is None


def test_enforce_tool_http_egress_allows_safe_target(monkeypatch):
    monkeypatch.setattr(settings, "TOOL_EGRESS_ALLOW_HOSTS", ["example.com"])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)
    monkeypatch.setattr(egress_policy, "is_allowlisted_host", lambda raw_url, allowed_hosts: True)

    target = SafeHttpTarget(
        scheme="https",
        original_host="example.com",
        port=443,
        resolved_ip="93.184.216.34",
        path_with_query="/a",
        fetch_url="https://93.184.216.34/a",
    )
    monkeypatch.setattr(egress_policy, "resolve_safe_http_target", lambda raw_url: target)

    assert egress_policy.enforce_tool_http_egress("https://example.com/a", tool="browse_url") == target

