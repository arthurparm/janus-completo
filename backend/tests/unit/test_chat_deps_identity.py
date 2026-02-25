from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.chat import deps as chat_deps


class _DummyHeaders(dict):
    def get(self, key, default=None):  # type: ignore[override]
        return super().get(key, default)


class _DummyRequest:
    def __init__(self, *, actor_user_id=None, headers=None):
        self.state = SimpleNamespace(actor_user_id=actor_user_id)
        self.headers = _DummyHeaders(headers or {})
        self.client = SimpleNamespace(host="127.0.0.1")


def test_resolve_authenticated_user_context_strict_requires_auth(monkeypatch):
    monkeypatch.setenv("CHAT_AUTH_ENFORCE_REQUIRED", "1")
    http = _DummyRequest(actor_user_id=None, headers={})

    ctx = chat_deps.resolve_authenticated_user_context(
        http,
        explicit_user_id=None,
        allow_anonymous_fallback=True,
        endpoint_label="/api/v1/chat/message",
    )

    assert ctx.user_id is None
    assert ctx.authenticated is False
    assert ctx.identity_source == "unknown"


def test_resolve_authenticated_user_context_transition_accepts_header(monkeypatch):
    monkeypatch.setenv("CHAT_AUTH_ENFORCE_REQUIRED", "0")
    monkeypatch.setenv("CHAT_AUTH_TRANSITION_WARN", "0")
    http = _DummyRequest(actor_user_id="u-123", headers={"X-User-Id": "u-123"})

    ctx = chat_deps.resolve_authenticated_user_context(
        http,
        explicit_user_id=None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/stream",
    )

    assert ctx.user_id == "u-123"
    assert ctx.identity_source in {"header", "actor"}
