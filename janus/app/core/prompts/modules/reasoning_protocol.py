"""
Reasoning Protocol Module - Task-specific reasoning guidelines.
Conditionally loads appropriate protocol based on intent.
"""

from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class ReasoningProtocolModule(PromptModule):
    """
    Provides structured reasoning guidelines tailored to the task type.
    Only loads when complex reasoning is needed (not for casual chat).
    """

    # Map intent types to reasoning protocol templates
    PROTOCOL_MAP = {
        IntentType.ANALYSIS: "capability_chain_of_thought",
        IntentType.TOOL_CREATION: "evolution_tool_specification",
        IntentType.CODE_REVIEW: "capability_code_review",
        IntentType.DEBUGGING: "capability_hypothesis_debugging",
        IntentType.RESEARCH: "capability_chain_of_thought",
        IntentType.QUESTION: "capability_chain_of_thought",
    }

    @property
    def name(self) -> str:
        return "reasoning_protocol"

    @property
    def priority(self) -> int:
        return 20  # Load after identity

    def is_applicable(self, intent: IntentType) -> bool:
        """Only load protocol for tasks requiring structured reasoning."""
        return intent in self.PROTOCOL_MAP

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Load and render appropriate reasoning protocol."""
        protocol_name = self.PROTOCOL_MAP.get(intent)

        if not protocol_name:
            return ""
        # Load protocol from database/files
        try:
            protocol_content = await get_prompt_with_fallback(protocol_name)
            if protocol_content:
                return f"\n{protocol_content}\n"
        except Exception:
            pass

        return ""
