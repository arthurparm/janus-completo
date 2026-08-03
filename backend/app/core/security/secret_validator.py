"""
Secret Management Module - Production Safety.

This module ensures that the Janus application does not start in 'production' mode
with insecure default passwords. This is a critical security measure.
"""
import structlog
from app.config import settings
from pydantic import SecretStr

logger = structlog.get_logger(__name__)

# Known insecure defaults that MUST be changed in production.
# Values are normalized to lowercase/trim during checks.
INSECURE_DEFAULTS: dict[str, set[str]] = {
    "NEO4J_PASSWORD": {"password", "change_me_neo4j_password", "__required__"},
    "POSTGRES_PASSWORD": {"janus_pass", "change_me_postgres_password", "__required__"},
    "RABBITMQ_PASSWORD": {"janus_pass", "change_me_rabbitmq_password", "__required__"},
    "AUTH_JWT_SECRET": {
        "",
        "none",
        "null",
        "changeme",
        "change_me",
        "dev_secret_change_me",
        "janus_dev_secret",
    },
    "AUDIT_LEDGER_HMAC_KEY": {
        "",
        "none",
        "null",
        "changeme",
        "change_me",
        "dev_secret_change_me",
        "janus_dev_secret",
    },
}


class InsecureConfigurationError(Exception):
    """Raised when critical production secrets are left at insecure defaults."""
    pass


def validate_production_secrets():
    """
    Checks if the application is running in 'production' mode and validates
    that no critical secrets are left at their insecure default values.

    Raises:
        InsecureConfigurationError: If the environment is 'production' and
            any secret is still set to a known insecure default.
    """
    environment = settings.ENVIRONMENT.lower()
    controlled_environments = {"production", "staging", "homologation", "development"}
    if environment not in controlled_environments:
        logger.info("Skipping deployed secret validation.", environment=settings.ENVIRONMENT)
        return

    alert_missing = []
    webhook_url = str(getattr(settings, "SECURITY_ALERT_WEBHOOK_URL", "") or "").strip()
    webhook_key = str(
        getattr(settings, "SECURITY_ALERT_WEBHOOK_HMAC_KEY", "") or ""
    ).strip()
    webhook_hosts = [
        str(host).strip().lower()
        for host in (getattr(settings, "SECURITY_ALERT_ALLOWED_HOSTS", None) or [])
        if str(host).strip()
    ]
    if not webhook_url or "__required__" in webhook_url.lower():
        alert_missing.append("SECURITY_ALERT_WEBHOOK_URL")
    if not webhook_key or webhook_key.lower() == "__required__":
        alert_missing.append("SECURITY_ALERT_WEBHOOK_HMAC_KEY")
    if not webhook_hosts or "__required__" in webhook_hosts:
        alert_missing.append("SECURITY_ALERT_ALLOWED_HOSTS")
    if alert_missing:
        raise InsecureConfigurationError(
            "Security alerting prerequisites are required: " + ", ".join(alert_missing)
        )

    if environment != "production":
        return

    logger.info("Validating production secrets...")

    insecure_found = []
    for setting_name, insecure_values in INSECURE_DEFAULTS.items():
        current_value = getattr(settings, setting_name, None)

        # Handle SecretStr
        if isinstance(current_value, SecretStr):
            current_value = current_value.get_secret_value()

        normalized = str(current_value or "").strip().lower()
        if normalized in insecure_values:
            insecure_found.append(setting_name)
            logger.error("log_error", message=f"Insecure default detected for: {setting_name}",
                         setting=setting_name)

    if insecure_found:
        error_msg = (
            f"CRITICAL: Cannot start in 'production' with insecure default values for: "
            f"{', '.join(insecure_found)}. "
            f"Please set these environment variables to secure values."
        )
        logger.critical(error_msg)
        raise InsecureConfigurationError(error_msg)

    logger.info("All production secrets are secure.")
