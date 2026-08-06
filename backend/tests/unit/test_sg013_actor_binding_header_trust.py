from app.config import settings
from app.core.infrastructure.auth import get_actor_user_id

from qa.auth_test_support import actor_from_test_request, issue_test_actor_token


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers
        self.state = type("State", (), {"trace_id": "test-trace", "actor_context": None})()


def test_get_actor_uses_signed_bearer_and_never_identity_header(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    token = issue_test_actor_token(99)
    request = _Req(headers={"Authorization": f"Bearer {token}", "X-User-Id": "12"})
    request.state.actor_context = actor_from_test_request(request)
    assert get_actor_user_id(request) == 99


def test_get_actor_rejects_identity_header_in_every_environment(monkeypatch):
    for environment in ("development", "staging", "production"):
        monkeypatch.setattr(settings, "ENVIRONMENT", environment)
        assert get_actor_user_id(_Req(headers={"X-User-Id": "12"})) is None
