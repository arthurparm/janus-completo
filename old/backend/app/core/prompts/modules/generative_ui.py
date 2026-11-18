"""
Generative UI Module - Optional UI blocks for structured answers.
"""

from app.core.infrastructure.prompt_loader import get_prompt
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class GenerativeUIModule(PromptModule):
    @property
    def name(self) -> str:
        return "generative_ui"

    @property
    def priority(self) -> int:
        return 45

    def is_applicable(self, intent: IntentType) -> bool:
        return intent in {IntentType.ANALYSIS, IntentType.QUESTION, IntentType.RESEARCH}

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        content = await get_prompt("generative_ui")
        return content or ""
