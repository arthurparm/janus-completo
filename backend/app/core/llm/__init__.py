"""LLM module exports with lightweight defaults and lazy heavy imports."""

from importlib import import_module
from typing import Any

from .types import ModelPriority, ModelRole

_LAZY_EXPORTS = {
    "LLMClient": ".client",
    "client": ".client",
    "factory": ".factory",
    "get_llm_client": ".client",
    "get_llm": ".router",
    "pricing": ".pricing",
    "response_cache": ".response_cache",
    "router": ".router",
    "resilience": ".resilience",
    "_llm_pool": ".resilience",
    "_provider_circuit_breakers": ".resilience",
    "invalidate_cache": ".resilience",
}
_LAZY_MODULE_EXPORTS = {"client", "factory", "pricing", "response_cache", "resilience", "router"}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        if name in _LAZY_MODULE_EXPORTS:
            value = module
        else:
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
    "client",
    "factory",
    "get_llm",
    "get_llm_client",
    "invalidate_cache",
    "pricing",
    "response_cache",
    "resilience",
    "router",
]
