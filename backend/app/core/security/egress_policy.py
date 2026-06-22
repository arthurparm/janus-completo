from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.core.security.url_safety import (
    SafeHttpTarget,
    is_allowlisted_host,
    parse_allowed_hosts_from_env,
    resolve_safe_http_target,
)
from app.repositories.observability_repository import record_audit_event_direct


def _try_parse_int(value: str | None) -> int | None:
    if not value:
        return None
    v = str(value).strip()
    if not v or not v.isdigit():
        return None
    try:
        return int(v)
    except Exception:
        return None


def _normalize_hosts(hosts: list[str] | set[str]) -> set[str]:
    return {str(h).strip().lower().strip(".") for h in hosts if str(h).strip()}


def _audit_egress_block(tool: str, raw_url: str, reason: str) -> None:
    """
    Registra tentativas de egress bloqueadas para auditoria contínua.

    Observação: se o banco não estiver disponível, o registro falha de forma silenciosa
    para não derrubar o fluxo do sistema, mas o bloqueio continua sendo aplicado.
    """
    user_id = _try_parse_int(USER_ID.get())
    trace_id = TRACE_ID.get()

    host: str | None = None
    scheme: str | None = None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(raw_url)
        host = parsed.hostname
        scheme = parsed.scheme
    except Exception:
        host = None
        scheme = None

    details: dict[str, Any] = {"reason": reason}
    if host:
        details["host"] = host
    if scheme:
        details["scheme"] = scheme

    try:
        record_audit_event_direct(
            user_id=user_id,
            endpoint="egress_policy",
            action="egress_blocked",
            tool=tool,
            status="blocked",
            trace_id=trace_id if trace_id and trace_id != "-" else None,
            details_json=details,
        )
    except Exception:
        return


def enforce_tool_http_egress(raw_url: str, tool: str) -> SafeHttpTarget | None:
    """
    Enforce de egress HTTP/HTTPS para ferramentas (tools).

    Política:
    - deny-by-default: se não houver allowlist configurada, bloqueia.
    - allowlist por host: exige host explicitamente permitido.
    - mitigação SSRF: valida DNS/IPs públicos e bloqueia alvos não públicos.
    - auditoria: toda tentativa bloqueada vira evento no audit ledger.

    Variável canônica:
    - TOOL_EGRESS_ALLOW_HOSTS (settings)

    Variáveis legadas (mantidas para compatibilidade operacional):
    - BROWSE_URL_ALLOWED_HOSTS
    - DYNAMIC_API_TOOL_ALLOWED_HOSTS
    """
    allowed_hosts = {h.strip().lower().strip(".") for h in settings.TOOL_EGRESS_ALLOW_HOSTS if h.strip()}
    allowed_hosts |= parse_allowed_hosts_from_env("BROWSE_URL_ALLOWED_HOSTS")
    allowed_hosts |= parse_allowed_hosts_from_env("DYNAMIC_API_TOOL_ALLOWED_HOSTS")
    if not (allowed_hosts and is_allowlisted_host(raw_url, allowed_hosts)):
        _audit_egress_block(tool=tool, raw_url=raw_url, reason="host_not_allowlisted")
        return None

    target = resolve_safe_http_target(raw_url)
    if not target:
        _audit_egress_block(tool=tool, raw_url=raw_url, reason="unsafe_url")
        return None

    return target


def _default_internal_hosts() -> set[str]:
    """
    Hosts internos esperados no runtime (containers/infra) que podem ser acessados por workers.

    Mantém o allowlist restrito, mas evita que o sistema quebre em operações internas
    (ex.: RabbitMQ management, Redis, Postgres etc.).
    """
    internal = {
        "postgres",
        "redis",
        "rabbitmq",
        "neo4j",
        "qdrant",
        "host.docker.internal",
    }

    try:
        from urllib.parse import urlparse

        neo = getattr(settings, "NEO4J_URI", "")
        if neo:
            parsed = urlparse(str(neo))
            if parsed.hostname:
                internal.add(parsed.hostname.lower().strip("."))
    except Exception:
        pass

    try:
        from urllib.parse import urlparse

        oll = getattr(settings, "OLLAMA_HOST", "")
        if oll:
            parsed = urlparse(str(oll))
            if parsed.hostname:
                internal.add(parsed.hostname.lower().strip("."))
    except Exception:
        pass

    try:
        from urllib.parse import urlparse

        vault_addr = getattr(settings, "VAULT_ADDR", "")
        if vault_addr:
            parsed = urlparse(str(vault_addr))
            if parsed.hostname:
                internal.add(parsed.hostname.lower().strip("."))
    except Exception:
        pass

    return internal


def _default_external_worker_hosts() -> set[str]:
    """
    Third-parties externos comumente habilitados no sistema.

    O objetivo não é “liberar geral”, e sim permitir que recursos explicitamente
    configurados (ex.: Google OAuth ou LLMs) funcionem sem exigir allowlists manuais
    para cada implantação, mantendo o conjunto mínimo de hosts.
    """
    hosts: set[str] = set()

    if getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or getattr(
        settings, "GOOGLE_OAUTH_CLIENT_SECRET", None
    ):
        hosts |= {
            "oauth2.googleapis.com",
            "www.googleapis.com",
            "gmail.googleapis.com",
        }

    if getattr(settings, "OPENAI_API_KEY", None):
        hosts.add("api.openai.com")

    if getattr(settings, "DEEPSEEK_API_KEY", None):
        hosts.add("api.deepseek.com")

    if getattr(settings, "XAI_API_KEY", None):
        hosts.add("api.x.ai")

    return hosts


def enforce_worker_http_egress(raw_url: str, tool: str) -> str | None:
    """
    Enforce de egress HTTP/HTTPS para workers.

    Política:
    - allowlist por host (settings.WORKER_EGRESS_ALLOW_HOSTS) + defaults internos.
    - bloqueia qualquer host fora da allowlist, registrando tentativa no audit ledger.

    Observação: ao contrário das ferramentas (tools), os workers normalmente chamam
    endpoints fixos e controlados pelo próprio sistema (ex.: Google APIs/LLMs).
    Aqui o foco é reduzir superfície de exfiltração/SSRF acidental via bugs/regressões.
    """
    allowed_hosts = _normalize_hosts(settings.WORKER_EGRESS_ALLOW_HOSTS)
    allowed_hosts |= _default_internal_hosts()
    allowed_hosts |= _default_external_worker_hosts()

    try:
        from urllib.parse import urlparse

        parsed = urlparse(raw_url)
        hostname = (parsed.hostname or "").strip().lower().strip(".")
        scheme = (parsed.scheme or "").strip().lower()
        if scheme not in {"http", "https"} or not hostname:
            _audit_egress_block(tool=tool, raw_url=raw_url, reason="invalid_url")
            return None
    except Exception:
        _audit_egress_block(tool=tool, raw_url=raw_url, reason="invalid_url")
        return None

    if hostname not in allowed_hosts:
        _audit_egress_block(tool=tool, raw_url=raw_url, reason="host_not_allowlisted")
        return None

    return raw_url
