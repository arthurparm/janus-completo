from app.core.infrastructure.auth import create_token, get_actor_user_id
from app.config import settings


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_get_actor_prefers_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    token = create_token(99, expires_in=3600)
    req = _Req(headers={"Authorization": f"Bearer {token}", "X-User-Id": "12"})

    assert get_actor_user_id(req) == 99


def test_get_actor_ignores_x_user_id_by_default(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    req = _Req(headers={"X-User-Id": "12"})

    assert get_actor_user_id(req) is None


def test_get_actor_allows_x_user_id_only_when_opted_in_non_production(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    req = _Req(headers={"X-User-Id": "12"})

    assert get_actor_user_id(req) == 12


def test_get_actor_never_allows_x_user_id_in_production(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    req = _Req(headers={"X-User-Id": "12"})

    assert get_actor_user_id(req) is None
