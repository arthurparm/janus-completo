import pytest
from app.config import settings
from app.core.infrastructure.windows_agent_client import WindowsAgentClient
from app.core.security import egress_policy
from app.core.security.url_safety import SafeHttpTarget


def test_asvs_lite_tool_egress_blocks_when_allowlist_is_empty(monkeypatch):
    monkeypatch.setattr(settings, "TOOL_EGRESS_ALLOW_HOSTS", [])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)

    assert (
        egress_policy.enforce_tool_http_egress(
            "https://example.com/a", tool="search_web"
        )
        is None
    )


def test_asvs_lite_tool_egress_returns_only_resolved_safe_target(monkeypatch):
    target = SafeHttpTarget(
        scheme="https",
        original_host="example.com",
        port=443,
        resolved_ip="93.184.216.34",
        path_with_query="/a",
        fetch_url="https://93.184.216.34/a",
    )
    monkeypatch.setattr(settings, "TOOL_EGRESS_ALLOW_HOSTS", ["example.com"])
    monkeypatch.setattr(egress_policy, "record_audit_event_direct", lambda **_: None)
    monkeypatch.setattr(egress_policy, "is_allowlisted_host", lambda *_: True)
    monkeypatch.setattr(egress_policy, "resolve_safe_http_target", lambda *_: target)

    result = egress_policy.enforce_tool_http_egress(
        "https://example.com/a", tool="search_web"
    )
    assert result == target
    assert result.fetch_url == "https://93.184.216.34/a"
    assert result.original_host == "example.com"


@pytest.mark.asyncio
async def test_asvs_lite_windows_agent_client_enforces_worker_egress(monkeypatch):
    client = WindowsAgentClient()

    monkeypatch.setattr(
        "app.core.infrastructure.windows_agent_client.enforce_worker_http_egress",
        lambda *_args, **_kwargs: None,
    )

    assert await client.speak("hi") is False
    assert await client.get_active_window_title() is None
    assert (await client.get_status()).get("status") == "blocked"

