import pytest

from app.config import settings
from app.core.memory import security


def test_encrypt_decrypt_with_keyring(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_KEYRING", {"k1": "material1", "k2": "material2"})
    monkeypatch.setattr(settings, "MEMORY_ACTIVE_KEY_ID", "k1")
    monkeypatch.setattr(settings, "MEMORY_ENCRYPTION_KEY", None)
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", None)

    cipher, enc = security.encrypt_text("hello", require_key=True)
    assert enc == "fernet"

    plain = security.decrypt_text(cipher, {"enc": "fernet", "kid": "k1"})
    assert plain == "hello"


def test_decrypt_works_after_rotation(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_KEYRING", {"k1": "material1", "k2": "material2"})
    monkeypatch.setattr(settings, "MEMORY_ACTIVE_KEY_ID", "k1")
    monkeypatch.setattr(settings, "MEMORY_ENCRYPTION_KEY", None)
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", None)

    cipher, enc = security.encrypt_text("hello", require_key=True)
    assert enc == "fernet"

    monkeypatch.setattr(settings, "MEMORY_ACTIVE_KEY_ID", "k2")

    plain = security.decrypt_text(cipher, {"enc": "fernet", "kid": "k1"})
    assert plain == "hello"


def test_encrypt_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_KEYRING", {})
    monkeypatch.setattr(settings, "MEMORY_ACTIVE_KEY_ID", None)
    monkeypatch.setattr(settings, "MEMORY_ENCRYPTION_KEY", None)
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", None)

    with pytest.raises(RuntimeError):
        security.encrypt_text("hello", require_key=True)

