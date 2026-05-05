from app.core.infrastructure.auth import create_token, get_actor_user_id, verify_token
from app.config import settings


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def test_verify_token_rejects_tampered_signature(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret")
    token = create_token(42, expires_in=3600)
    body, sig = token.split(".", 1)
    tampered = f"{body}.{sig[:-1]}{'A' if sig[-1] != 'A' else 'B'}"

    assert verify_token(tampered) is None


def test_verify_token_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret")
    token = create_token(42, expires_in=-1)

    assert verify_token(token) is None


def test_get_actor_ignores_x_user_id_by_default(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    assert get_actor_user_id(_Req(headers={"X-User-Id": "12"})) is None
