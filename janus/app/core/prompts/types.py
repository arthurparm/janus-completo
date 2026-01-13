"""
Base types and enums for the modular prompt system.
"""

from enum import Enum


class IntentType(str, Enum):
    """
    Classification of user intent to determine which prompt modules to load.
    """

    # Analysis & Research
    ANALYSIS = "analysis"
    QUESTION = "question"
    RESEARCH = "research"

    # Code & Tools
    TOOL_CREATION = "tool_creation"
    SCRIPT_GENERATION = "script_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"

    # Documentation
    DOCUMENTATION = "documentation"
    EXPLANATION = "explanation"

    # Execution
    TASK_EXECUTION = "task_execution"
    SYSTEM_COMMAND = "system_command"

    # Conversation
    CASUAL_CHAT = "casual_chat"
    CAPABILITIES_QUERY = "capabilities_query"

    # Special
    UNKNOWN = "unknown"
