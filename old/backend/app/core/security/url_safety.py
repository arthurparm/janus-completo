from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class SafeHttpTarget:
    scheme: str
    original_host: str
    port: int
    resolved_ip: str
    path_with_query: str
    fetch_url: str


def parse_allowed_hosts_from_env(env_var: str) -> set[str]:
    return {
        h.strip().lower().strip(".")
        for h in os.getenv(env_var, "").split(",")
        if h.strip()
    }


def is_allowlisted_host(raw_url: str, allowed_hosts: set[str]) -> bool:
    if not allowed_hosts:
        return False
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    return hostname.lower().strip(".") in allowed_hosts


def resolve_safe_http_target(raw_url: str) -> SafeHttpTarget | None:
    """
    Resolve e valida um alvo HTTP/HTTPS com mitigação SSRF.

    Regras principais:
    - Bloqueia credenciais embutidas na URL (user:pass@host).
    - Bloqueia localhost e domínios .localhost.
    - Resolve DNS e bloqueia qualquer IP não público (private/loopback/link-local/etc).
    - Para HTTP, retorna um fetch_url baseado em IP (reduz risco de DNS rebinding).
    - Para HTTPS, preserva o hostname no fetch_url para não quebrar validação TLS/SNI,
      mas mantém o IP resolvido para auditoria e diagnósticos.
    """
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return None

    if parsed.scheme not in {"http", "https"}:
        return None

    if parsed.username or parsed.password:
        return None

    hostname = parsed.hostname
    if not hostname:
        return None

    lowered = hostname.lower().strip(".")
    if lowered in {"localhost"} or lowered.endswith(".localhost"):
        return None

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addrinfo = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except Exception:
        return None

    resolved_ip: str | None = None
    for entry in addrinfo:
        ip_text = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_text)
        except ValueError:
            return None
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return None
        if resolved_ip is None:
            resolved_ip = ip_text

    if not resolved_ip:
        return None

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    default_port = 443 if parsed.scheme == "https" else 80
    if parsed.scheme == "http":
        netloc = resolved_ip if port == default_port else f"{resolved_ip}:{port}"
        fetch_url = f"{parsed.scheme}://{netloc}{path}"
    else:
        netloc = hostname if port == default_port else f"{hostname}:{port}"
        fetch_url = f"{parsed.scheme}://{netloc}{path}"

    return SafeHttpTarget(
        scheme=parsed.scheme,
        original_host=hostname,
        port=port,
        resolved_ip=resolved_ip,
        path_with_query=path,
        fetch_url=fetch_url,
    )
