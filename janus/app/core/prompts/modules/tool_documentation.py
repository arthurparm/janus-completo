"""
Tool Documentation Module - Dynamic, intent-based tool documentation.
Only documents tools relevant to the current intent.
"""

from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType
from app.core.tools import action_registry


class ToolDocumentationModule(PromptModule):
    """
    Generates compact tool documentation for only the relevant tools.
    """

    INTENT_TOOLS = {
        IntentType.TOOL_CREATION: ["evolve_tool"],
        IntentType.SCRIPT_GENERATION: ["write_file", "execute_shell"],
        IntentType.CODE_REVIEW: ["read_file", "list_directory", "query_knowledge_graph"],
        IntentType.DEBUGGING: [
            "read_file",
            "execute_shell",
            "query_knowledge_graph",
            "find_related_concepts",
        ],
        IntentType.QUESTION: [
            "query_knowledge_graph",
            "find_related_concepts",
            "read_file",
        ],
        IntentType.ANALYSIS: [
            "query_knowledge_graph",
            "read_file",
            "list_directory",
        ],
        IntentType.DOCUMENTATION: ["read_file", "write_file", "query_knowledge_graph"],
    }

    CORE_TOOLS = ["query_knowledge_graph", "read_file"]

    @property
    def name(self) -> str:
        return "tool_documentation"

    @property
    def priority(self) -> int:
        return 40  # Load after protocols

    def is_applicable(self, intent: IntentType) -> bool:
        """Load tools for all intents except casual chat."""
        return intent != IntentType.CASUAL_CHAT

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Generate compact tool documentation."""
        relevant_tool_names = self.INTENT_TOOLS.get(intent, self.CORE_TOOLS)

        try:
            all_tools = action_registry.list_tools()
        except Exception:
            return ""

        relevant_tools = [t for t in all_tools if t.name in relevant_tool_names]
        if not relevant_tools:
            return ""

        tool_entries = "\n".join(
            f"- {tool.name}: {(tool.description or '').split('\n')[0]}" for tool in relevant_tools
        )

        return await get_formatted_prompt("tool_documentation", tool_entries=tool_entries)
