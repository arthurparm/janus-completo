from app.core.memory import security


def test_memory_encryption_uses_only_its_dedicated_legacy_key(monkeypatch):
    security._fernet_by_key_id.clear()
    monkeypatch.setattr(security.settings, "MEMORY_ENCRYPTION_KEY", None)

    encrypted, method = security.encrypt_text("segredo")

    assert method is None
    assert encrypted == "segredo"
