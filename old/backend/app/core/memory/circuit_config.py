"""
Configuration module for circuit breaker and Qdrant resilience settings.
"""

import os
from dataclasses import dataclass


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 3
    recovery_timeout: int = 30
    half_open_max_calls: int = 5
    half_open_success_threshold: int = 3


@dataclass
class QdrantTimeoutConfig:
    """Configuration for Qdrant timeout settings."""

    search_timeout: float = 30.0
    connection_timeout: float = 10.0
    read_timeout: float = 25.0
    write_timeout: float = 25.0
    health_check_timeout: float = 5.0


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""

    max_attempts: int = 3
    initial_backoff: float = 0.5
    max_backoff: float = 5.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class ResilienceConfig:
    """Comprehensive resilience configuration."""

    circuit_breaker: CircuitBreakerConfig
    qdrant_timeouts: QdrantTimeoutConfig
    retry: RetryConfig
    enable_auto_recovery: bool = True
    auto_recovery_interval: int = 60  # seconds
    enable_circuit_breaker_metrics: bool = True
    enable_timeout_tuning: bool = False


def load_resilience_config() -> ResilienceConfig:
    """Load resilience configuration from environment variables."""

    # Circuit breaker settings
    cb_config = CircuitBreakerConfig(
        failure_threshold=int(os.getenv("LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3")),
        recovery_timeout=int(os.getenv("LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "30")),
        half_open_max_calls=int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "5")),
        half_open_success_threshold=int(
            os.getenv("CIRCUIT_BREAKER_HALF_OPEN_SUCCESS_THRESHOLD", "3")
        ),
    )

    # Qdrant timeout settings
    timeout_config = QdrantTimeoutConfig(
        search_timeout=float(os.getenv("QDRANT_SEARCH_TIMEOUT_SECONDS", "30.0")),
        connection_timeout=float(os.getenv("QDRANT_CONNECTION_TIMEOUT_SECONDS", "10.0")),
        read_timeout=float(os.getenv("QDRANT_READ_TIMEOUT_SECONDS", "25.0")),
        write_timeout=float(os.getenv("QDRANT_WRITE_TIMEOUT_SECONDS", "25.0")),
        health_check_timeout=float(os.getenv("QDRANT_HEALTH_CHECK_TIMEOUT_SECONDS", "5.0")),
    )

    # Retry settings
    retry_config = RetryConfig(
        max_attempts=int(os.getenv("LLM_RETRY_MAX_ATTEMPTS", "3")),
        initial_backoff=float(os.getenv("LLM_RETRY_INITIAL_BACKOFF_SECONDS", "0.5")),
        max_backoff=float(os.getenv("LLM_RETRY_MAX_BACKOFF_SECONDS", "5.0")),
        backoff_multiplier=float(os.getenv("RETRY_BACKOFF_MULTIPLIER", "2.0")),
        jitter=os.getenv("RETRY_JITTER_ENABLED", "true").lower() == "true",
    )

    return ResilienceConfig(
        circuit_breaker=cb_config,
        qdrant_timeouts=timeout_config,
        retry=retry_config,
        enable_auto_recovery=os.getenv("ENABLE_AUTO_RECOVERY", "true").lower() == "true",
        auto_recovery_interval=int(os.getenv("AUTO_RECOVERY_INTERVAL_SECONDS", "60")),
        enable_circuit_breaker_metrics=os.getenv("ENABLE_CIRCUIT_BREAKER_METRICS", "true").lower()
        == "true",
        enable_timeout_tuning=os.getenv("ENABLE_TIMEOUT_TUNING", "false").lower() == "true",
    )


# Global configuration instance
RESILIENCE_CONFIG = load_resilience_config()
