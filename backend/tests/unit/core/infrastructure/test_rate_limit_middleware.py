import pytest
from fastapi import Request, Response

from app.core.infrastructure.rate_limit_middleware import RateLimitMiddleware


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
async def test_chat_rate_limit_still_blocks_non_unlimited_user(monkeypatch):
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
    assert response.status_code == 503
