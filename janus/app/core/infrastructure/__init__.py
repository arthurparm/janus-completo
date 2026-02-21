"""Infrastructure module exports with lazy loading."""

from importlib import import_module
from typing import Any

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    # Message Broker
    "MessageBroker": (".message_broker", "MessageBroker"),
    "initialize_broker": (".message_broker", "initialize_broker"),
    "close_broker": (".message_broker", "close_broker"),
    "get_broker": (".message_broker", "get_broker"),
    # Resilience
    "CircuitBreaker": (".resilience", "CircuitBreaker"),
    "resilient": (".resilience", "resilient"),
    # Context Manager
    "ContextManager": (".context_manager", "ContextManager"),
    "context_manager": (".context_manager", "context_manager"),
    # Python Sandbox
    "PythonSandbox": (".python_sandbox", "PythonSandbox"),
    "python_sandbox": (".python_sandbox", "python_sandbox"),
    # Filesystem
    "read_file": (".filesystem_manager", "read_file"),
    "write_file": (".filesystem_manager", "write_file"),
    "list_directory": (".filesystem_manager", "list_directory"),
    "filesystem_manager": (".filesystem_manager", ""),
    # Prompt Loader
    "PromptLoader": (".prompt_loader", "PromptLoader"),
    "prompt_loader": (".prompt_loader", "prompt_loader"),
    "get_prompt": (".prompt_loader", "get_prompt"),
    "get_prompt_advanced": (".prompt_loader", "get_prompt_advanced"),
    # Middleware
    "CorrelationMiddleware": (".correlation_middleware", "CorrelationMiddleware"),
    "RateLimitMiddleware": (".rate_limit_middleware", "RateLimitMiddleware"),
    # Logging
    "setup_logging": (".logging_config", "setup_logging"),
    "setup_tracing": (".logging_config", "setup_tracing"),
    # Enums
    "AgentType": (".enums", "AgentType"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if not target:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = module if not attr_name else getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    # Message Broker
    "MessageBroker",
    "initialize_broker",
    "close_broker",
    "get_broker",
    # Resilience
    "CircuitBreaker",
    "resilient",
    # Context Manager
    "ContextManager",
    "context_manager",
    # Python Sandbox
    "PythonSandbox",
    "python_sandbox",
    # Filesystem Manager
    "read_file",
    "write_file",
    "list_directory",
    "filesystem_manager",
    # Prompt Loader
    "PromptLoader",
    "prompt_loader",
    "get_prompt",
    "get_prompt_advanced",
    # Middleware
    "CorrelationMiddleware",
    "RateLimitMiddleware",
    # Logging
    "setup_logging",
    "setup_tracing",
    # Enums
    "AgentType",
]
