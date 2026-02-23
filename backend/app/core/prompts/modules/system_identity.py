"""
System Identity Module - Base personality and behavioral guidelines.
Migrated from janus_identity_jarvis.txt for consistent, elegant identity.
"""

from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType
from app.core.infrastructure.prompt_fallback import get_formatted_prompt


class SystemIdentityModule(PromptModule):
    """
    Provides core system identity, personality traits, and security rules.
    Always loaded regardless of intent.
    """

    @property
    def name(self) -> str:
        return "system_identity"

    @property
    def priority(self) -> int:
        return 10  # Load first

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Render system identity prompt."""
        persona = context.persona or "assistant"

        return await get_formatted_prompt("system_identity", persona=persona)
