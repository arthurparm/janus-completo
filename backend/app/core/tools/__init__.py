"""Tools module exports with lazy loading for optional integrations."""

from importlib import import_module
from typing import Any

from .action_module import (
    ActionRegistry,
    PermissionLevel,
    ToolCategory,
    ToolMetadata,
    action_registry,
    get_all_tools,
    get_tools_by_category,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "get_tools_for_agent": (".safe_tools", "get_tools_for_agent"),
    "meta_agent_tools": (".safe_tools", "meta_agent_tools"),
    "recall_experiences": (".safe_tools", "recall_experiences"),
    "recall_working_memory": (".safe_tools", "recall_working_memory"),
    "unified_tools": (".safe_tools", "unified_tools"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if not target:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "ActionRegistry",
    "PermissionLevel",
    "ToolCategory",
    "ToolMetadata",
    "action_registry",
    "get_all_tools",
    "get_tools_by_category",
    "get_tools_for_agent",
    "meta_agent_tools",
    "recall_experiences",
    "recall_working_memory",
    "unified_tools",
]
