from app.config import settings
from app.core.infrastructure.auth import create_token, get_actor_user_id


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_get_actor_uses_signed_bearer_and_never_identity_header(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret-with-sufficient-entropy")
    token = create_token(99, expires_in=3600)
    request = _Req(headers={"Authorization": f"Bearer {token}", "X-User-Id": "12"})
    assert get_actor_user_id(request) == 99


def test_get_actor_rejects_identity_header_in_every_environment(monkeypatch):
    for environment in ("development", "staging", "production"):
        monkeypatch.setattr(settings, "ENVIRONMENT", environment)
        assert get_actor_user_id(_Req(headers={"X-User-Id": "12"})) is None
