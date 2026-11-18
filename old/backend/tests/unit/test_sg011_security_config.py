import pytest
from app.config import AppSettings
from app.core.security import secret_validator
from pydantic import SecretStr, ValidationError


def _production_identity_settings(profile: str = "user") -> dict[str, object]:
    return {
        "ENVIRONMENT": "production",
        "JANUS_API_PROFILE": profile,
        "OIDC_ADMIN_GROUP": "janus-administrators",
        "OIDC_ISSUER": "https://idp.example.com",
        "OIDC_JWKS_URL": "https://idp.example.com/jwks",
        "OIDC_AUTHORIZATION_ENDPOINT": "https://idp.example.com/authorize",
        "OIDC_SERVICE_ISSUER": "https://service-idp.example.com",
        "OIDC_SERVICE_JWKS_URL": "https://service-idp.example.com/jwks",
        "OIDC_SERVICE_TOKEN_URL": "https://service-idp.example.com/token",
        "ADMIN_FACADE_CLIENT_SECRET": "not-a-real-secret",
    }


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
        **_production_identity_settings(),
        CORS_ALLOW_ORIGINS='["https://janus.example.com","https://app.example.com"]',
    )

    assert settings.CORS_ALLOW_ORIGINS == [
        "https://janus.example.com",
        "https://app.example.com",
    ]


def test_all_test_profile_is_rejected_in_deployed_environments():
    with pytest.raises(ValidationError, match="all-test is restricted to local tests"):
        AppSettings(
            _env_file=None,
            ENVIRONMENT="production",
            JANUS_API_PROFILE="all-test",
            OIDC_ADMIN_GROUP="janus-administrators",
        )


def test_oidc_clock_skew_is_fixed_and_audiences_are_distinct():
    with pytest.raises(ValidationError, match="fixed at 30 seconds"):
        AppSettings(_env_file=None, OIDC_CLOCK_SKEW_SECONDS=60)
    with pytest.raises(ValidationError, match="audiences must be distinct"):
        AppSettings(
            _env_file=None,
            OIDC_USER_AUDIENCE="same-audience",
            OIDC_SERVICE_AUDIENCE="same-audience",
        )


def test_deployed_user_profile_requires_real_oidc_and_facade_credentials():
    values = _production_identity_settings()
    values["ADMIN_FACADE_CLIENT_SECRET"] = None
    with pytest.raises(ValidationError, match="ADMIN_FACADE_CLIENT_SECRET"):
        AppSettings(_env_file=None, **values)
    values = _production_identity_settings()
    values["OIDC_ISSUER"] = "https://idp.invalid"
    with pytest.raises(ValidationError, match="placeholder host"):
        AppSettings(_env_file=None, **values)


def test_validate_production_secrets_rejects_insecure_defaults(monkeypatch):
    monkeypatch.setattr(secret_validator.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(secret_validator.settings, "NEO4J_PASSWORD", SecretStr("password"))
    monkeypatch.setattr(secret_validator.settings, "POSTGRES_PASSWORD", SecretStr("janus_pass"))
    monkeypatch.setattr(secret_validator.settings, "RABBITMQ_PASSWORD", SecretStr("janus_pass"))

    with pytest.raises(secret_validator.InsecureConfigurationError):
        secret_validator.validate_production_secrets()


def test_validate_production_secrets_rejects_required_placeholder(monkeypatch):
    monkeypatch.setattr(secret_validator.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(secret_validator.settings, "NEO4J_PASSWORD", SecretStr("__REQUIRED__"))
    monkeypatch.setattr(secret_validator.settings, "POSTGRES_PASSWORD", SecretStr("__REQUIRED__"))
    monkeypatch.setattr(secret_validator.settings, "RABBITMQ_PASSWORD", SecretStr("__REQUIRED__"))

    with pytest.raises(secret_validator.InsecureConfigurationError):
        secret_validator.validate_production_secrets()


def test_validate_production_secrets_passes_with_secure_values(monkeypatch):
    monkeypatch.setattr(secret_validator.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(secret_validator.settings, "NEO4J_PASSWORD", SecretStr("n3o4j-Secure-987"))
    monkeypatch.setattr(
        secret_validator.settings, "POSTGRES_PASSWORD", SecretStr("PostgresSecure-123")
    )
    monkeypatch.setattr(secret_validator.settings, "RABBITMQ_PASSWORD", SecretStr("RabbitSecure-456"))
    monkeypatch.setattr(secret_validator.settings, "AUDIT_LEDGER_HMAC_KEY", "AuditSecure-789")
    monkeypatch.setattr(
        secret_validator.settings,
        "SECURITY_ALERT_WEBHOOK_URL",
        "https://security.example.invalid/events",
    )
    monkeypatch.setattr(secret_validator.settings, "SECURITY_ALERT_WEBHOOK_HMAC_KEY", "AlertSecure-123")
    monkeypatch.setattr(
        secret_validator.settings,
        "SECURITY_ALERT_ALLOWED_HOSTS",
        ["security.example.invalid"],
    )

    secret_validator.validate_production_secrets()
