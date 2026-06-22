import pytest

from app.core.security.url_safety import SafeHttpTarget
from app.core.tools.agent_tools import browse_url
from app.core.infrastructure.windows_agent_client import WindowsAgentClient


def test_asvs_lite_browse_url_blocks_when_egress_policy_blocks(monkeypatch):
    monkeypatch.setattr(
        "app.core.tools.agent_tools.enforce_tool_http_egress",
        lambda *_args, **_kwargs: None,
    )

    assert "política de egress/SSRF" in browse_url("https://example.com/a")


def test_asvs_lite_browse_url_uses_safe_fetch_url_and_host_header(monkeypatch):
    target = SafeHttpTarget(
        scheme="https",
        original_host="example.com",
        port=443,
        resolved_ip="93.184.216.34",
        path_with_query="/a",
        fetch_url="https://93.184.216.34/a",
    )
    monkeypatch.setattr(
        "app.core.tools.agent_tools.enforce_tool_http_egress",
        lambda *_args, **_kwargs: target,
    )

    captured: dict[str, object] = {}

    class DummyResponse:
        def __init__(self):
            self.content = b"<html><body>Hello</body></html>"
            self.encoding = "utf-8"

        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            captured["follow_redirects"] = kwargs.get("follow_redirects")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            captured["url"] = url
            captured["headers"] = headers or {}
            return DummyResponse()

    monkeypatch.setattr("app.core.tools.agent_tools.httpx.Client", DummyClient)

    result = browse_url("https://example.com/a")
    assert "Hello" in result
    assert captured.get("url") == target.fetch_url
    assert (captured.get("headers") or {}).get("Host") == target.original_host


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

