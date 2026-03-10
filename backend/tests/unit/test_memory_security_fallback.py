from app.core.memory import security


def test_memory_encryption_falls_back_to_auth_secret(monkeypatch):
    monkeypatch.setattr(security, "_fernet_obj", None)
    monkeypatch.setattr(security.settings, "MEMORY_ENCRYPTION_KEY", None)
    monkeypatch.setattr(security.settings, "AUTH_JWT_SECRET", "JwtSecure-789")

    encrypted, method = security.encrypt_text("segredo")

    assert method == "fernet"
    assert encrypted != "segredo"
