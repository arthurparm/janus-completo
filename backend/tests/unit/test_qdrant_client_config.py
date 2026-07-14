from __future__ import annotations

from types import SimpleNamespace

from app.core.memory.qdrant_client_config import build_qdrant_client_kwargs
from pydantic import SecretStr


def test_build_qdrant_client_kwargs_uses_http_without_ca_by_default() -> None:
    settings = SimpleNamespace(
        QDRANT_HOST="qdrant",
        QDRANT_PORT=6333,
        QDRANT_HTTPS=False,
        QDRANT_TLS_CA_CERT="/run/secrets/janus/qdrant/ca.pem",
        QDRANT_API_KEY=SecretStr("secret"),
        QDRANT_CHECK_COMPATIBILITY=False,
    )

    kwargs = build_qdrant_client_kwargs(settings, timeout=20)

    assert kwargs == {
        "host": "qdrant",
        "port": 6333,
        "https": False,
        "timeout": 20,
        "api_key": "secret",
        "check_compatibility": False,
    }


def test_build_qdrant_client_kwargs_adds_verify_for_https_ca() -> None:
    settings = SimpleNamespace(
        QDRANT_HOST="host.docker.internal",
        QDRANT_PORT=6333,
        QDRANT_HTTPS=True,
        QDRANT_TLS_CA_CERT="/run/secrets/janus/qdrant/ca.pem",
        QDRANT_API_KEY=SecretStr("secret"),
        QDRANT_CHECK_COMPATIBILITY=False,
    )

    kwargs = build_qdrant_client_kwargs(settings)

    assert kwargs["https"] is True
    assert kwargs["api_key"] == "secret"
    assert kwargs["check_compatibility"] is False
    assert kwargs["verify"] == "/run/secrets/janus/qdrant/ca.pem"


def test_build_qdrant_client_kwargs_prefers_explicit_runtime_overrides() -> None:
    settings = SimpleNamespace(
        QDRANT_HOST="qdrant",
        QDRANT_PORT=6333,
        QDRANT_HTTPS=False,
        QDRANT_TLS_CA_CERT="/run/secrets/janus/qdrant/ca.pem",
        QDRANT_API_KEY=SecretStr("settings-secret"),
        QDRANT_CHECK_COMPATIBILITY=True,
    )

    kwargs = build_qdrant_client_kwargs(
        settings,
        host="runtime-host",
        port=7443,
        https=True,
        api_key="runtime-secret",
        prefer_grpc=True,
    )

    assert kwargs["host"] == "runtime-host"
    assert kwargs["port"] == 7443
    assert kwargs["https"] is True
    assert kwargs["api_key"] == "runtime-secret"
    assert kwargs["check_compatibility"] is True
    assert kwargs["prefer_grpc"] is True
    assert kwargs["verify"] == "/run/secrets/janus/qdrant/ca.pem"
