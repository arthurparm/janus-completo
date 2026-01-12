"""
Secret Management Module - Production Safety.

This module ensures that the Janus application does not start in 'production' mode
with insecure default passwords. This is a critical security measure.
"""
import structlog
from pydantic import SecretStr

from app.config import settings

logger = structlog.get_logger(__name__)

# Known insecure defaults that MUST be changed in production
INSECURE_DEFAULTS = {
    "NEO4J_PASSWORD": "password",
    "MYSQL_PASSWORD": "janus_pass",
    "MYSQL_ROOT_PASSWORD": "janus_root",
    "RABBITMQ_PASSWORD": "janus_pass",
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
    if settings.ENVIRONMENT.lower() != "production":
        logger.info("Skipping secret validation (non-production environment).",
                    environment=settings.ENVIRONMENT)
        return

    logger.info("Validating production secrets...")

    insecure_found = []
    for setting_name, insecure_value in INSECURE_DEFAULTS.items():
        current_value = getattr(settings, setting_name, None)

        # Handle SecretStr
        if isinstance(current_value, SecretStr):
            current_value = current_value.get_secret_value()

        if current_value == insecure_value:
            insecure_found.append(setting_name)
            logger.error(f"Insecure default detected for: {setting_name}",
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
