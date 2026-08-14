from __future__ import annotations

from typing import Any

import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.repositories import user_repository
from app.repositories.user_repository import OAuthTokenRepository
from app.services import oauth_token_security_service as security


def test_oauth_envelope_round_trip_with_real_fernet_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "MEMORY_ENCRYPTION_PROVIDER", "keyring")
    monkeypatch.setattr(settings, "MEMORY_KEYRING", {})
    monkeypatch.setattr(settings, "MEMORY_ACTIVE_KEY_ID", None)
    monkeypatch.setattr(
        settings,
        "MEMORY_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )

    protected = security.protect_oauth_token("real-secret-token")

    assert "real-secret-token" not in protected
    assert security.reveal_oauth_token(protected) == "real-secret-token"


def test_oauth_envelope_encrypts_and_reveals_without_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        security,
        "encrypt_text",
        lambda value, **_kwargs: (f"cipher-{value}", "fernet"),
    )
    monkeypatch.setattr(
        security,
        "decrypt_text",
        lambda value, metadata: value.removeprefix("cipher-"),
    )

    protected = security.protect_oauth_token("secret-token")

    assert protected != "secret-token"
    assert "cipher-secret-token" in protected
    assert security.is_protected_oauth_token(protected)
    assert security.reveal_oauth_token(protected) == "secret-token"


def test_oauth_envelope_fails_closed_without_encryption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_encrypt(_value: str, **_kwargs: object) -> tuple[str, None]:
        raise RuntimeError("no key")

    monkeypatch.setattr(security, "encrypt_text", fail_encrypt)

    with pytest.raises(security.OAuthTokenProtectionError, match="unavailable"):
        security.protect_oauth_token("secret-token")


def test_oauth_envelope_supports_legacy_read_but_rejects_broken_ciphertext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert security.reveal_oauth_token("legacy-plaintext") == "legacy-plaintext"
    monkeypatch.setattr(security, "decrypt_text", lambda value, metadata: value)
    protected = "janus-oauth:v1:fernet:undecryptable"

    with pytest.raises(security.OAuthTokenProtectionError, match="decryption failed"):
        security.reveal_oauth_token(protected)


class _Query:
    def __init__(self, session: _Session) -> None:
        self.session = session

    def filter(self, *_args: object) -> _Query:
        return self

    def first(self) -> Any:
        return self.session.current


class _Session:
    def __init__(self, current: Any = None) -> None:
        self.current = current
        self.commits: list[tuple[str, str | None]] = []

    def query(self, _model: object) -> _Query:
        return _Query(self)

    def add(self, token: Any) -> None:
        self.current = token

    def commit(self) -> None:
        self.commits.append((self.current.access_token, self.current.refresh_token))

    def refresh(self, _token: object) -> None:
        return None

    def expunge(self, _token: object) -> None:
        return None


def test_oauth_repository_persists_envelopes_and_returns_plain_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session()
    monkeypatch.setattr(
        user_repository,
        "protect_oauth_token",
        lambda value: f"protected:{value}",
    )
    monkeypatch.setattr(
        user_repository,
        "reveal_oauth_token",
        lambda value: value.removeprefix("protected:") if value else None,
    )

    token = OAuthTokenRepository(session).upsert(
        user_id=7,
        provider="google",
        access_token="access",
        refresh_token="refresh",
        expires_at=None,
    )

    assert session.commits == [("protected:access", "protected:refresh")]
    assert token.access_token == "access"
    assert token.refresh_token == "refresh"


def test_oauth_repository_lazily_migrates_legacy_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = type(
        "StoredToken",
        (),
        {"access_token": "legacy-access", "refresh_token": "legacy-refresh"},
    )()
    session = _Session(token)
    monkeypatch.setattr(user_repository, "is_protected_oauth_token", lambda value: False)
    monkeypatch.setattr(user_repository, "reveal_oauth_token", lambda value: value)
    monkeypatch.setattr(
        user_repository,
        "protect_oauth_token",
        lambda value: f"protected:{value}",
    )

    loaded = OAuthTokenRepository(session).get(user_id=7, provider="google")

    assert session.commits == [("protected:legacy-access", "protected:legacy-refresh")]
    assert loaded is not None
    assert loaded.access_token == "legacy-access"
    assert loaded.refresh_token == "legacy-refresh"
