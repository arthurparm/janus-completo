from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.auth import LocalResetRequest, local_request_reset
from app.config import settings


class _RepoStub:
    def __init__(self, user):
        self._user = user
        self.saved_token_hash = None
        self.saved_expires_at = None

    def get_by_email(self, _email: str):
        return self._user

    def set_reset_token(self, _user_id: int, token_hash: str | None, expires_at=None):
        self.saved_token_hash = token_hash
        self.saved_expires_at = expires_at
        return True


@pytest.mark.asyncio
async def test_request_reset_does_not_return_token_in_development_even_when_disabled_flag(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "AUTH_RESET_RETURN_TOKEN", False)

    repo = _RepoStub(user=SimpleNamespace(id=10))
    resp = await local_request_reset(
        LocalResetRequest(email="dev@example.com"), request=SimpleNamespace(), repo=repo
    )

    assert resp.status == "ok"
    assert resp.reset_token is None
    assert repo.saved_token_hash is not None


@pytest.mark.asyncio
async def test_request_reset_returns_token_only_in_test_env_with_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "AUTH_RESET_RETURN_TOKEN", True)

    repo = _RepoStub(user=SimpleNamespace(id=11))
    resp = await local_request_reset(
        LocalResetRequest(email="dev@example.com"), request=SimpleNamespace(), repo=repo
    )

    assert resp.status == "ok"
    assert isinstance(resp.reset_token, str) and len(resp.reset_token) > 10


@pytest.mark.asyncio
async def test_request_reset_never_returns_token_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "AUTH_RESET_RETURN_TOKEN", True)

    repo = _RepoStub(user=SimpleNamespace(id=12))
    resp = await local_request_reset(
        LocalResetRequest(email="prod@example.com"), request=SimpleNamespace(), repo=repo
    )

    assert resp.status == "ok"
    assert resp.reset_token is None
    assert repo.saved_token_hash is not None


@pytest.mark.asyncio
async def test_request_reset_returns_token_in_ci_with_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "ci")
    monkeypatch.setattr(settings, "AUTH_RESET_RETURN_TOKEN", True)

    repo = _RepoStub(user=SimpleNamespace(id=13))
    resp = await local_request_reset(
        LocalResetRequest(email="ci@example.com"), request=SimpleNamespace(), repo=repo
    )

    assert resp.status == "ok"
    assert isinstance(resp.reset_token, str) and len(resp.reset_token) > 10


@pytest.mark.asyncio
async def test_request_reset_does_not_return_token_in_staging(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "AUTH_RESET_RETURN_TOKEN", True)

    repo = _RepoStub(user=SimpleNamespace(id=14))
    resp = await local_request_reset(
        LocalResetRequest(email="staging@example.com"), request=SimpleNamespace(), repo=repo
    )

    assert resp.status == "ok"
    assert resp.reset_token is None
