"""
Prompt Composer Service - Orchestrates modular prompt construction.
Replaces monolithic prompt_builder_service with efficient, composable architecture.
"""

import logging
from functools import lru_cache
from typing import Any

from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.intent_classifier import IntentClassifier
from app.core.prompts.modules import (
    ContextCompressionModule,
    ReasoningProtocolModule,
    SystemIdentityModule,
    TaskSpecificModule,
    ToolDocumentationModule,
)
from app.core.prompts.types import IntentType
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class CompiledPrompt:
    """
    Result of prompt composition.
    Contains final prompt text and metadata.
    """

    def __init__(
        self,
        text: str,
        intent: IntentType,
        modules_used: list[str],
        token_count: int,
    ):
        self.text = text
        self.intent = intent
        self.modules_used = modules_used
        self.token_count = token_count

    def __str__(self) -> str:
        return self.text


class PromptComposer:
    """
    Composes prompts by selecting and rendering relevant modules.
    Provides caching, token optimization, and modular composition.
    """

    def __init__(self, prompt_service: PromptService | None = None):
        """
        Initialize composer with optional prompt service for dynamic prompts.

        Args:
            prompt_service: Service for fetching dynamic prompts from DB
        """
        self.prompt_service = prompt_service
        self.intent_classifier = IntentClassifier()

        # Initialize all modules
        self.modules: list[PromptModule] = [
            SystemIdentityModule(),
            ReasoningProtocolModule(),
            ContextCompressionModule(),
            ToolDocumentationModule(),
            TaskSpecificModule(),
        ]

        # Sort by priority
        self.modules.sort(key=lambda m: m.priority)

    async def compose(
        self,
        intent: IntentType,
        context: ConversationContext,
    ) -> CompiledPrompt:
        """
        Compose final prompt from relevant modules.

        Args:
            intent: Classified user intent
            context: Conversation context

        Returns:
            Compiled prompt ready for LLM
        """
        # Select applicable modules
        applicable_modules = [m for m in self.modules if m.is_applicable(intent)]

        logger.info(
            f"[PROMPT_COMPOSE] Intent={intent.value}, "
            f"Modules={[m.name for m in applicable_modules]}"
        )

        # Render each module
        sections = []
        modules_used = []

        for module in applicable_modules:
            try:
                rendered = await module.render(intent, context)
                if rendered:  # Only add non-empty sections
                    sections.append(rendered)
                    modules_used.append(module.name)
            except Exception as e:
                logger.error(f"[PROMPT_COMPOSE] Error rendering module {module.name}: {e}")
                # Continue with other modules

        # Add current user message
        sections.append(f"\n**User**: {context.current_message}\n")
        sections.append("**Assistant**:")

        # Compile final prompt
        final_prompt = "\n\n".join(sections)

        # Estimate tokens
        token_count = self._estimate_tokens(final_prompt)

        logger.info(
            f"[PROMPT_COMPOSE] Compiled {len(modules_used)} modules, " f"~{token_count} tokens"
        )

        return CompiledPrompt(
            text=final_prompt,
            intent=intent,
            modules_used=modules_used,
            token_count=token_count,
        )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (chars / 4)."""
        return len(text) // 4 if text else 0

    @lru_cache(maxsize=128)
    def _get_cache_key(
        self,
        intent: IntentType,
        persona: str,
        message_hash: int,
    ) -> str:
        """Generate cache key for composed prompts."""
        return f"{intent.value}:{persona}:{message_hash}"


# Singleton instance for reuse
_composer_instance: PromptComposer | None = None


def get_prompt_composer(prompt_service: PromptService | None = None) -> PromptComposer:
    """
    Get or create singleton PromptComposer instance.

    Args:
        prompt_service: Optional prompt service

    Returns:
        PromptComposer instance
    """
    global _composer_instance
    if _composer_instance is None:
        _composer_instance = PromptComposer(prompt_service)
    return _composer_instance
