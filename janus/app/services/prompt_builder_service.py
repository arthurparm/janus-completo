"""
Prompt Builder Service - Modular Architecture
Delegates to PromptComposer for efficient, intent-based prompt generation.
"""

import logging
from typing import Any

from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class PromptBuilderService:
    """
    Service for building LLM prompts using modular composition.
    Uses intent classification and selective module loading for token efficiency.
    """

    def __init__(self, prompt_service: PromptService | None = None):
        """
        Initialize prompt builder.

        Args:
            prompt_service: Optional service for dynamic prompt loading
        """
        self.prompt_service = prompt_service

    async def build_prompt(
        self,
        persona: str,
        history: list[dict[str, Any]],
        new_user_message: str,
        summary: str | None,
        relevant_memories: str | None = None,
    ) -> str:
        """
        Build complete prompt for LLM using modular composition.

        Uses intent-based module selection for optimal token efficiency:
        - Classifies user intent (tool creation, question, etc.)
        - Loads only relevant prompt modules
        - Compresses context intelligently
        - Returns optimized prompt

        Args:
            persona: Conversation persona/style
            history: Previous messages in conversation
            new_user_message: Current user message
            summary: Optional conversation summary
            relevant_memories: Optional long-term memories

        Returns:
            Compiled prompt string ready for LLM
        """
        from app.core.prompts.context import ConversationContext, Message
        from app.core.prompts.intent_classifier import IntentClassifier
        from app.services.prompt_composer_service import get_prompt_composer

        logger.info(
            "[PROMPT_BUILD] Building prompt for message: '%s...'",
            new_user_message[:100] if new_user_message else "(empty)",
        )

        # Classify intent
        classifier = IntentClassifier()
        intent = classifier.classify(new_user_message)

        # Build context
        context = ConversationContext(
            history=[Message(role=h.get("role", "user"), text=h.get("text", "")) for h in history],
            current_message=new_user_message,
            summary=summary,
            relevant_memories=relevant_memories,
            persona=persona,
        )

        # Compose prompt using modular system
        composer = get_prompt_composer(self.prompt_service)
        compiled = await composer.compose(intent, context)

        logger.info(
            f"[PROMPT_BUILD] ✅ Composed {len(compiled.modules_used)} modules, "
            f"~{compiled.token_count} tokens (intent={intent.value})"
        )

        return compiled.text

    async def is_capabilities_query(self, message: str) -> bool:
        """Check if message is asking about capabilities."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        return classifier.is_capabilities_query(message)

    async def is_tool_request(self, message: str) -> bool:
        """Check if message is requesting tool creation."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        return classifier.is_tool_request(message)

    async def is_script_request(self, message: str) -> bool:
        """Check if message is requesting script generation."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        return classifier.is_script_request(message)
