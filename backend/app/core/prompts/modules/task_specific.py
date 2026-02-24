"""
Task-Specific Instructions Module - Intent-specific guidelines.
Provides clear, actionable instructions only for the current task type.
"""

from app.core.infrastructure.prompt_loader import get_prompt
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class TaskSpecificModule(PromptModule):
    """
    Provides focused instructions specific to the detected intent.
    """

    TASK_PROMPTS = {
        IntentType.TOOL_CREATION: "task_tool_creation_protocol",
        IntentType.SCRIPT_GENERATION: "task_script_generation_protocol",
        IntentType.CODE_REVIEW: "task_code_review_protocol",
        IntentType.DEBUGGING: "task_debugging_protocol",
        IntentType.QUESTION: "task_question_protocol",
    }

    @property
    def name(self) -> str:
        return "task_specific"

    @property
    def priority(self) -> int:
        return 50  # Load last

    def is_applicable(self, intent: IntentType) -> bool:
        """Load instructions only for tasks with specific protocols."""
        return intent in self.TASK_PROMPTS

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Return task-specific instructions."""
        prompt_name = self.TASK_PROMPTS.get(intent)
        if not prompt_name:
            return ""

        try:
            content = await get_prompt(prompt_name)
            return content or ""
        except Exception:
            return ""
