from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.services import productivity_oauth_token_exchange_service as service


class _Response:
    def __init__(
        self,
        status_code: int,
        payload: object = None,
        *,
        json_error: ValueError | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://oauth2.googleapis.com/token")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("provider error", request=request, response=response)

    def json(self) -> object:
        if self._json_error:
            raise self._json_error
        return self._payload


def _client_factory(
    response: _Response | Exception,
    captured: dict[str, object],
) -> Callable[..., object]:
    class _Client:
        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> _Response:
            captured["url"] = url
            captured.update(kwargs)
            if isinstance(response, Exception):
                raise response
            return response

    return lambda **_kwargs: _Client()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_exchange_uses_exact_oauth_contract_and_returns_typed_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    response = _Response(
        200,
        {"access_token": "access", "refresh_token": "refresh", "expires_in": 3600},
    )
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(response, captured))

    result = await service.exchange_google_authorization_code(
        code="code",
        client_id="client",
        client_secret="secret",
        redirect_uri="https://janus.example/integrations/google/callback",
    )

    assert result == service.GoogleOAuthTokens("access", "refresh", 3600)
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["data"] == {
        "code": "code",
        "client_id": "client",
        "client_secret": "secret",
        "redirect_uri": "https://janus.example/integrations/google/callback",
        "grant_type": "authorization_code",
    }


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("response", "expected_error"),
    [
        (_Response(400), service.GoogleOAuthCodeRejectedError),
        (_Response(401), service.GoogleOAuthExchangeProviderError),
        (_Response(503), service.GoogleOAuthExchangeProviderError),
        (httpx.ReadTimeout("timeout"), service.GoogleOAuthExchangeTimeoutError),
        (httpx.ConnectError("network"), service.GoogleOAuthExchangeProviderError),
        (
            _Response(200, json_error=ValueError("invalid json")),
            service.GoogleOAuthExchangeProviderError,
        ),
        (
            _Response(200, {"refresh_token": "refresh", "expires_in": 3600}),
            service.GoogleOAuthExchangeProviderError,
        ),
        (
            _Response(200, {"access_token": "access", "expires_in": True}),
            service.GoogleOAuthExchangeProviderError,
        ),
    ],
)
async def test_exchange_normalizes_provider_failures(
    monkeypatch: pytest.MonkeyPatch,
    response: _Response | Exception,
    expected_error: type[Exception],
) -> None:
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(response, {}))

    with pytest.raises(expected_error):
        await service.exchange_google_authorization_code(
            code="code",
            client_id="client",
            client_secret="secret",
            redirect_uri="https://janus.example/callback",
        )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_exchange_fails_closed_before_network_when_egress_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service,
        "enforce_worker_http_egress",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(httpx, "AsyncClient", pytest.fail)

    with pytest.raises(service.GoogleOAuthExchangeBlockedError):
        await service.exchange_google_authorization_code(
            code="code",
            client_id="client",
            client_secret="secret",
            redirect_uri="https://janus.example/callback",
        )
