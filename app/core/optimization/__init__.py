"""
Módulo de otimização - Auto-otimização, Reflexion e aprendizado.
"""
from .self_optimization import SelfOptimizationEngine, get_self_optimization_engine
from .reflexion_core import ReflexionCore, get_reflexion_core

__all__ = [
    "SelfOptimizationEngine",
    "get_self_optimization_engine",
    "ReflexionCore",
    "get_reflexion_core"
]
