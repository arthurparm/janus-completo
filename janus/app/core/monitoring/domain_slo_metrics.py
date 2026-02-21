"""Domain-level SLO metrics and helpers for OQ-002."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

TRACKED_DOMAINS = {"chat", "rag", "tools", "workers"}

DOMAIN_REQUESTS_TOTAL = Counter(
    "janus_domain_requests_total",
    "Total HTTP requests by domain and outcome (5xx considered error).",
    ["domain", "outcome"],  # outcome: success|error
)

DOMAIN_REQUEST_LATENCY_SECONDS = Histogram(
    "janus_domain_request_latency_seconds",
    "HTTP request latency by domain.",
    ["domain"],
    # Tuned to cover chat/rag p95 targets with reasonable bucket granularity.
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 8.0, 13.0, 21.0),
)


def derive_domain_from_path(path: str | None) -> str:
    value = str(path or "").strip().lower()
    if not value:
        return "other"
    if value.startswith("/api/v1/"):
        tail = value[len("/api/v1/") :]
    elif value.startswith("/"):
        tail = value[1:]
    else:
        tail = value
    first = tail.split("/", 1)[0].strip()
    if first in TRACKED_DOMAINS:
        return first
    return "other"


def is_http_error(status_code: int | None) -> bool:
    if status_code is None:
        return False
    try:
        return int(status_code) >= 500
    except Exception:
        return False

