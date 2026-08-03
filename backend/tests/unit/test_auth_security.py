from app.config import settings
from app.core.infrastructure.auth import create_token, get_actor_user_id, verify_token


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_verify_token_rejects_tampered_signature(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret-with-sufficient-entropy")
    token = create_token(42, expires_in=3600)
    header, body, signature = token.split(".")
    tampered = f"{header}.{body}.{signature[:-1]}{'A' if signature[-1] != 'A' else 'B'}"

    assert verify_token(tampered) is None


def test_verify_token_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret-with-sufficient-entropy")
    token = create_token(42, expires_in=-1)

    assert verify_token(token) is None


def test_get_actor_ignores_x_user_id_by_default(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    assert get_actor_user_id(_Req(headers={"X-User-Id": "12"})) is None
