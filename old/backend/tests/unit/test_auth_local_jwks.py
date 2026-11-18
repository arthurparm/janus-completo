from __future__ import annotations

import pytest
from app.core.infrastructure import auth


def test_local_development_jwks_allows_only_explicit_loopback_hosts(monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "development")
    auth._jwks_client.cache_clear()

    client = auth._jwks_client("http://janus-dev-idp:8400/.well-known/jwks.json", 30)
    assert client is not None

    auth._jwks_client.cache_clear()
    with pytest.raises(auth.TokenValidationError) as error:
        auth._jwks_client("http://idp.example/.well-known/jwks.json", 30)
    assert error.value.reason == "jwks_url_not_https"


def test_deployed_environment_still_requires_https_for_local_hosts(monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "production")
    auth._jwks_client.cache_clear()

    with pytest.raises(auth.TokenValidationError) as error:
        auth._jwks_client("http://localhost:8400/.well-known/jwks.json", 30)
    assert error.value.reason == "jwks_url_not_https"
