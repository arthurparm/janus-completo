"""
Módulo de otimização - Auto-otimização, Reflexion e aprendizado.
"""
from .reflexion_core import ReflexionSession, ReflexionConfig, arun_with_reflexion
from .self_optimization import SelfOptimizationCycle, self_optimization_cycle, SystemMonitor

__all__ = [
    "ReflexionSession",
    "ReflexionConfig",
    "arun_with_reflexion",
    "SelfOptimizationCycle",
    "self_optimization_cycle",
    "SystemMonitor"
]
