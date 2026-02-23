import pytest
from pydantic import SecretStr, ValidationError

from app.config import AppSettings
from app.core.security import secret_validator


def test_cors_defaults_to_localhost_origins_in_development():
    settings = AppSettings(_env_file=None, ENVIRONMENT="development")

    assert "http://localhost:4200" in settings.CORS_ALLOW_ORIGINS
    assert "http://127.0.0.1:4200" in settings.CORS_ALLOW_ORIGINS


def test_cors_rejects_wildcard_in_production():
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None, ENVIRONMENT="production", CORS_ALLOW_ORIGINS="*")


def test_cors_accepts_explicit_json_origins_in_production():
    settings = AppSettings(
        _env_file=None,
        ENVIRONMENT="production",
        CORS_ALLOW_ORIGINS='["https://janus.example.com","https://app.example.com"]',
    )

    assert settings.CORS_ALLOW_ORIGINS == [
        "https://janus.example.com",
        "https://app.example.com",
    ]


def test_validate_production_secrets_rejects_insecure_defaults(monkeypatch):
    monkeypatch.setattr(secret_validator.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(secret_validator.settings, "NEO4J_PASSWORD", SecretStr("password"))
    monkeypatch.setattr(secret_validator.settings, "POSTGRES_PASSWORD", SecretStr("janus_pass"))
    monkeypatch.setattr(secret_validator.settings, "RABBITMQ_PASSWORD", "janus_pass")
    monkeypatch.setattr(secret_validator.settings, "AUTH_JWT_SECRET", "dev_secret_change_me")

    with pytest.raises(secret_validator.InsecureConfigurationError):
        secret_validator.validate_production_secrets()


def test_validate_production_secrets_passes_with_secure_values(monkeypatch):
    monkeypatch.setattr(secret_validator.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(secret_validator.settings, "NEO4J_PASSWORD", SecretStr("n3o4j-Secure-987"))
    monkeypatch.setattr(
        secret_validator.settings, "POSTGRES_PASSWORD", SecretStr("PostgresSecure-123")
    )
    monkeypatch.setattr(secret_validator.settings, "RABBITMQ_PASSWORD", "RabbitSecure-456")
    monkeypatch.setattr(secret_validator.settings, "AUTH_JWT_SECRET", "JwtSecure-789")

    secret_validator.validate_production_secrets()
