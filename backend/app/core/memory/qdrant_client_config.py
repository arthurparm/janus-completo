from __future__ import annotations

from typing import Any


def resolve_secret_value(value: Any) -> str | None:
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_qdrant_client_kwargs(
    settings: Any,
    *,
    timeout: int | float | None = None,
    host: str | None = None,
    port: int | None = None,
    grpc_port: int | None = None,
    prefer_grpc: bool | None = None,
    api_key: str | None = None,
    https: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build canonical AsyncQdrantClient arguments from Janus settings."""
    client_kwargs: dict[str, Any] = {
        "host": host if host is not None else settings.QDRANT_HOST,
        "port": port if port is not None else settings.QDRANT_PORT,
        "https": bool(getattr(settings, "QDRANT_HTTPS", False) if https is None else https),
    }
    if timeout is not None:
        client_kwargs["timeout"] = timeout
    if grpc_port is not None:
        client_kwargs["grpc_port"] = grpc_port
    if prefer_grpc is not None:
        client_kwargs["prefer_grpc"] = prefer_grpc

    resolved_api_key = api_key if api_key is not None else resolve_secret_value(
        getattr(settings, "QDRANT_API_KEY", None)
    )
    if resolved_api_key:
        client_kwargs["api_key"] = resolved_api_key

    ca_cert = str(getattr(settings, "QDRANT_TLS_CA_CERT", "") or "").strip()
    if client_kwargs["https"] and ca_cert:
        client_kwargs["verify"] = ca_cert

    client_kwargs.update(extra)
    return client_kwargs
