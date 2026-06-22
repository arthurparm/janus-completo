from types import SimpleNamespace

from app.api.v1.endpoints.chat import deps as chat_deps


class _DummyHeaders(dict):
    def get(self, key, default=None):  # type: ignore[override]
        if key in self:
            return super().get(key, default)
        normalized = str(key).lower()
        for existing_key, value in self.items():
            if str(existing_key).lower() == normalized:
                return value
        return default


class _DummyRequest:
    def __init__(self, *, actor_user_id: str | None, headers=None):
        self.state = SimpleNamespace(actor_user_id=actor_user_id)
        self.headers = _DummyHeaders(headers or {})
        self.client = SimpleNamespace(host="127.0.0.1")


def test_resolve_authenticated_user_context_strict_requires_auth(monkeypatch):
    http = _DummyRequest(actor_user_id=None, headers={})

    ctx = chat_deps.resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=True,
        endpoint_label="/api/v1/chat/message",
    )
    assert ctx.authenticated is False
    assert ctx.identity_source == "unknown"


def test_resolve_authenticated_user_context_rejects_x_user_id_without_bearer():
    http = _DummyRequest(actor_user_id=None, headers={"X-User-Id": "u-123"})

    ctx = chat_deps.resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/stream",
    )
    assert ctx.user_id is None
    assert ctx.identity_source == "unknown"
    assert ctx.authenticated is False


def test_resolve_authenticated_user_context_accepts_bearer_bound_actor():
    http = _DummyRequest(actor_user_id="42", headers={"Authorization": "Bearer token"})

    ctx = chat_deps.resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=True,
        endpoint_label="/api/v1/chat/message",
    )

    assert ctx.user_id == "42"
    assert ctx.identity_source == "actor"
    assert ctx.authenticated is True
