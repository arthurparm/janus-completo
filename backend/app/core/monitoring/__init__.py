"""Monitoring module exports with lazy loading."""

from importlib import import_module
from typing import Any

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "start_auto_healer": (".auto_healer", "start_auto_healer"),
    "HealthCheckResult": (".health_monitor", "HealthCheckResult"),
    "HealthMonitor": (".health_monitor", "HealthMonitor"),
    "get_health_monitor": (".health_monitor", "get_health_monitor"),
    "PoisonPillHandler": (".poison_pill_handler", "PoisonPillHandler"),
    "get_poison_pill_handler": (".poison_pill_handler", "get_poison_pill_handler"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if not target:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "HealthCheckResult",
    "HealthMonitor",
    "PoisonPillHandler",
    "get_health_monitor",
    "get_poison_pill_handler",
    "start_auto_healer",
]
