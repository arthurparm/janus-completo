"""
Módulo de monitoramento - Health checks, poison pills e observabilidade.
"""

from .auto_healer import start_auto_healer
from .health_monitor import HealthCheckResult, HealthMonitor, get_health_monitor
from .poison_pill_handler import PoisonPillHandler, get_poison_pill_handler

__all__ = [
    "HealthCheckResult",
    "HealthMonitor",
    "PoisonPillHandler",
    "get_health_monitor",
    "get_poison_pill_handler",
    "start_auto_healer",
]
