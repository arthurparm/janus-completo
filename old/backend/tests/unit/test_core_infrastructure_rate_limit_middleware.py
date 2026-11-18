import pytest
from fastapi import Request, Response

from app.core.infrastructure.rate_limit_middleware import RateLimitMiddleware
from app.core.security.actor_context import ActorContext, AuthMethod


def _request(
    *,
    actor_context: ActorContext | None = None,
    actor_user_id: str | None = None,
    client_ip: str = "127.0.0.1",
) -> Request:
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/v1/tools/",
        "headers": [],
        "client": (client_ip, 5000),
        "query_string": b"",
    })
    request.state.actor_context = actor_context
    request.state.actor_user_id = actor_user_id
    return request


def test_authenticated_requests_use_isolated_user_bucket():
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    actor = ActorContext.authenticated(
        actor_id="42",
        roles=("USER",),
        auth_method=AuthMethod.OIDC,
        trace_id="trace-rate-limit",
    )

    key, rate, burst, scope = middleware._rate_limit_subject(
        _request(actor_context=actor)
    )

    assert key == "rate_limit:user:42"
    assert rate == middleware.rate_key
    assert burst == middleware.burst_key
    assert scope == "user"


def test_legacy_actor_user_id_state_is_not_an_identity_source(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    monkeypatch.setattr(
        "app.core.infrastructure.rate_limit_middleware.get_actor_user_id",
        lambda _request: None,
    )

    key, _rate, _burst, scope = middleware._rate_limit_subject(
        _request(actor_user_id="forged", client_ip="10.0.0.9")
    )

    assert key == "rate_limit:ip:10.0.0.9"
    assert scope == "IP"


def test_anonymous_requests_use_source_ip_bucket(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    monkeypatch.setattr(
        "app.core.infrastructure.rate_limit_middleware.get_actor_user_id",
        lambda _request: None,
    )

    key, rate, burst, scope = middleware._rate_limit_subject(_request(client_ip="10.0.0.8"))

    assert key == "rate_limit:ip:10.0.0.8"
    assert rate == middleware.rate_ip
    assert burst == middleware.burst_ip
    assert scope == "IP"


@pytest.mark.asyncio
async def test_chat_rate_limit_bypasses_unlimited_user(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    middleware.fail_closed = True
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.is_chat_unlimited_request", lambda _request: True)
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.settings.REDIS_ENABLED", False)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/chat/stream/101",
        "headers": [],
        "client": ("127.0.0.1", 5000),
        "query_string": b"",
    }
    request = Request(scope)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=204)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_chat_rate_limit_uses_local_fallback_when_redis_unavailable(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    middleware.fail_closed = True
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.is_chat_unlimited_request", lambda _request: False)
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.settings.REDIS_ENABLED", False)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/chat/stream/101",
        "headers": [],
        "client": ("127.0.0.1", 5000),
        "query_string": b"",
    }
    request = Request(scope)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=204)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_chat_rate_limit_local_fallback_blocks_after_bucket_exhaustion(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    middleware.fail_closed = True
    middleware.burst_ip = 1
    middleware.rate_ip = 0.1
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.is_chat_unlimited_request", lambda _request: False)
    monkeypatch.setattr("app.core.infrastructure.rate_limit_middleware.settings.REDIS_ENABLED", False)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/chat/stream/101",
        "headers": [],
        "client": ("127.0.0.1", 5000),
        "query_string": b"",
    }
    request = Request(scope)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=204)

    first_response = await middleware.dispatch(request, call_next)
    second_response = await middleware.dispatch(request, call_next)

    assert first_response.status_code == 204
    assert second_response.status_code == 429


@pytest.mark.asyncio
async def test_policy_resolution_error_does_not_bypass_rate_limit(monkeypatch):
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    middleware.fail_closed = True
    monkeypatch.setattr(
        "app.core.infrastructure.rate_limit_middleware.resolve_endpoint_policy",
        lambda _request: (_ for _ in ()).throw(AttributeError("route unavailable")),
    )
    monkeypatch.setattr(
        "app.core.infrastructure.rate_limit_middleware.is_chat_unlimited_request",
        lambda _request: False,
    )
    monkeypatch.setattr(
        "app.core.infrastructure.rate_limit_middleware.settings.REDIS_ENABLED", False
    )
    request = _request(client_ip="10.0.0.10")

    async def call_next(_request: Request) -> Response:
        return Response(status_code=204)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 503
