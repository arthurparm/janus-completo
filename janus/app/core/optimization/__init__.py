"""
Módulo de otimização - Auto-otimização, Reflexion e aprendizado.
"""

from .reflexion_core import ReflexionConfig, ReflexionSession
from .self_optimization import SelfOptimizationCycle, SystemMonitor, self_optimization_cycle

__all__ = [
    "ReflexionConfig",
    "ReflexionSession",
    "SelfOptimizationCycle",
    "SystemMonitor",
    "self_optimization_cycle",
]
