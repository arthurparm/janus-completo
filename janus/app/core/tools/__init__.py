"""
Módulo de ferramentas - Tools para agentes e Action Module.
"""

from .action_module import (
    ActionRegistry,
    DynamicToolGenerator,
    PermissionLevel,
    ToolCategory,
    ToolMetadata,  # Adicionado ToolMetadata
    action_registry,
    get_all_tools,
    get_tools_by_category,
)
from .agent_tools import (
    get_tools_for_agent,
    meta_agent_tools,
    recall_experiences,
    recall_working_memory,
    unified_tools,
)
from .faulty_tools import (
    faulty_calculator,
    flaky_api_call,
    get_faulty_tools,
    inconsistent_file_reader,
    memory_leaking_processor,
    reset_faulty_tools,
    slow_database_query,
    unreliable_weather_api,
    validate_tool_output,
)

__all__ = [
    "ActionRegistry",
    "DynamicToolGenerator",
    "PermissionLevel",
    "ToolCategory",
    "ToolMetadata",  # Adicionado ToolMetadata
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
]
