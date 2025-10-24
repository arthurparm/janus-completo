"""
Módulo de LLM - Gerenciamento de modelos de linguagem e roteamento.
"""
from .llm_manager import (
    LLMClient,
    ModelRole,
    ModelPriority,
    get_llm,
    get_llm_client,
    invalidate_cache,
    _llm_cache,
    _provider_circuit_breakers
)

__all__ = [
    "LLMClient",
    "ModelRole",
    "ModelPriority",
    "get_llm",
    "get_llm_client",
    "invalidate_cache",
    "_llm_cache",
    "_provider_circuit_breakers"
]
