"""Prometheus metrics for Auto-Healer.

Keep these definitions separate from the Auto-Healer runtime so app bootstrap can
register metrics without importing worker dependencies or starting healing logic.
"""

from prometheus_client import Counter

AUTO_HEALER_STEP_FAILURES = Counter(
    "auto_healer_step_failures_total",
    "Total de falhas por etapa do Auto-Healer",
    ["step"],
)
AUTO_HEALER_STEP_ATTEMPTS = Counter(
    "auto_healer_step_attempts_total",
    "Total de tentativas por etapa do Auto-Healer",
    ["step"],
)
AUTO_HEALER_STEP_SUCCESSES = Counter(
    "auto_healer_step_successes_total",
    "Total de sucessos por etapa do Auto-Healer",
    ["step"],
)
