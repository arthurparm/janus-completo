"""Tools module exports with lazy loading for optional integrations."""

from importlib import import_module
from typing import Any

from .action_module import (
    ActionRegistry,
    DynamicToolGenerator,
    PermissionLevel,
    ToolCategory,
    ToolMetadata,
    action_registry,
    get_all_tools,
    get_tools_by_category,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # agent_tools
    "get_tools_for_agent": (".agent_tools", "get_tools_for_agent"),
    "meta_agent_tools": (".agent_tools", "meta_agent_tools"),
    "recall_experiences": (".agent_tools", "recall_experiences"),
    "recall_working_memory": (".agent_tools", "recall_working_memory"),
    "unified_tools": (".agent_tools", "unified_tools"),
    # faulty_tools
    "faulty_calculator": (".faulty_tools", "faulty_calculator"),
    "flaky_api_call": (".faulty_tools", "flaky_api_call"),
    "get_faulty_tools": (".faulty_tools", "get_faulty_tools"),
    "inconsistent_file_reader": (".faulty_tools", "inconsistent_file_reader"),
    "memory_leaking_processor": (".faulty_tools", "memory_leaking_processor"),
    "reset_faulty_tools": (".faulty_tools", "reset_faulty_tools"),
    "slow_database_query": (".faulty_tools", "slow_database_query"),
    "unreliable_weather_api": (".faulty_tools", "unreliable_weather_api"),
    "validate_tool_output": (".faulty_tools", "validate_tool_output"),
    # external_cli_tools
    "codex_exec": (".external_cli_tools", "codex_exec"),
    "codex_review": (".external_cli_tools", "codex_review"),
    "codex_login": (".external_cli_tools", "codex_login"),
    "jules_new": (".external_cli_tools", "jules_new"),
    "jules_pull": (".external_cli_tools", "jules_pull"),
    "register_external_cli_tools": (".external_cli_tools", "register_external_cli_tools"),
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
    "DynamicToolGenerator",
    "PermissionLevel",
    "ToolCategory",
    "ToolMetadata",
    "action_registry",
    "faulty_calculator",
    "flaky_api_call",
    "get_all_tools",
    "get_faulty_tools",
    "get_tools_by_category",
    "get_tools_for_agent",
    "inconsistent_file_reader",
    "memory_leaking_processor",
    "meta_agent_tools",
    "recall_experiences",
    "recall_working_memory",
    "reset_faulty_tools",
    "slow_database_query",
    "unified_tools",
    "unreliable_weather_api",
    "validate_tool_output",
    "codex_exec",
    "codex_review",
    "codex_login",
    "jules_new",
    "jules_pull",
    "register_external_cli_tools",
]
