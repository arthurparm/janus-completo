"""LLM module exports with lightweight defaults and lazy heavy imports."""

from importlib import import_module
from typing import Any

from .types import ModelPriority, ModelRole

_LLM_MANAGER_EXPORTS = {
    "LLMClient",
    "_llm_pool",
    "_provider_circuit_breakers",
    "get_llm",
    "get_llm_client",
    "invalidate_cache",
}


def __getattr__(name: str) -> Any:
    if name in _LLM_MANAGER_EXPORTS:
        module = import_module(".llm_manager", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "LLMClient",
    "ModelPriority",
    "ModelRole",
    "_llm_pool",
    "_provider_circuit_breakers",
    "get_llm",
    "get_llm_client",
    "invalidate_cache",
]
