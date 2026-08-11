from __future__ import annotations

import asyncio

import pytest
from app.api.v1.endpoints import admin_actions
from fastapi import HTTPException
from pydantic import SecretStr


class _Response:
    status_code = 200

    def json(self) -> dict[str, str]:
        return {"access_token": "local-service-token"}


class _Client:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, *, data, auth):
        return _Response()


def _configure(monkeypatch: pytest.MonkeyPatch, *, environment: str, url: str) -> None:
    monkeypatch.setattr(admin_actions.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(admin_actions.settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(admin_actions.settings, "OIDC_SERVICE_TOKEN_URL", url)
    monkeypatch.setattr(
        admin_actions.settings,
        "ADMIN_FACADE_CLIENT_SECRET",
        SecretStr("local-secret"),
    )


def test_development_allows_only_the_internal_local_idp(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(
        monkeypatch,
        environment="development",
        url="http://janus-dev-idp:8400/token",
    )

    token = asyncio.run(admin_actions._service_token(frozenset({"ops:read"})))

    assert token == "local-service-token"


@pytest.mark.parametrize(
    ("environment", "url"),
    [
        ("development", "http://idp.example/token"),
        ("production", "http://localhost:8400/token"),
    ],
)
def test_insecure_service_token_endpoints_remain_rejected(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    url: str,
) -> None:
    _configure(monkeypatch, environment=environment, url=url)

    with pytest.raises(HTTPException) as error:
        asyncio.run(admin_actions._service_token(frozenset({"ops:read"})))

    assert error.value.status_code == 503
