from __future__ import annotations

from app.core.security.url_safety import is_allowlisted_host, resolve_safe_http_target


def test_is_allowlisted_host_requires_explicit_host_match():
    allowed = {"example.com"}
    assert is_allowlisted_host("https://example.com/path", allowed) is True
    assert is_allowlisted_host("https://sub.example.com/path", allowed) is False


def test_resolve_safe_http_target_blocks_loopback_and_private_ranges():
    assert resolve_safe_http_target("http://127.0.0.1/") is None
    assert resolve_safe_http_target("http://localhost/") is None
    assert resolve_safe_http_target("http://10.0.0.1/") is None
    assert resolve_safe_http_target("http://192.168.0.10/") is None
    assert resolve_safe_http_target("http://172.16.0.10/") is None


def test_resolve_safe_http_target_rejects_userinfo():
    assert resolve_safe_http_target("http://user:pass@127.0.0.1/") is None

