"""
Context Compression Module - Intelligent history summarization.
Uses Chain-of-Density approach to compress long conversations.
"""

import logging

from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.types import IntentType

logger = logging.getLogger(__name__)


class ContextCompressionModule(PromptModule):
    """
    Compresses conversation history to reduce token consumption.
    - Short histories (<= 3 messages): no compression
    - Long histories: Chain-of-Density summarization
    """

    SHORT_HISTORY_THRESHOLD = 3
    MAX_COMPRESSED_TOKENS = 200

    @property
    def name(self) -> str:
        return "context_compression"

    @property
    def priority(self) -> int:
        return 30  # Load after reasoning, before tools

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Render compressed conversation context."""
        if not context.history and not context.summary and not context.relevant_memories:
            return ""

        blocks = []

        if context.summary:
            blocks.append(
                await get_formatted_prompt(
                    "context_summary_section",
                    summary=context.summary,
                )
            )

        if context.relevant_memories:
            blocks.append(
                await get_formatted_prompt(
                    "context_memories_section",
                    memories=context.relevant_memories,
                )
            )

        if context.history:
            if context.history_length <= self.SHORT_HISTORY_THRESHOLD:
                recent_history = "\n".join(self._format_raw_history(context.history))
                blocks.append(
                    await get_formatted_prompt(
                        "context_recent_conversation_section",
                        recent_history=recent_history,
                    )
                )
            else:
                compressed = await self._compress_history(context.history)
                blocks.append(
                    await get_formatted_prompt(
                        "context_compressed_conversation_section",
                        compressed_history=compressed,
                    )
                )

        return "\n".join(blocks) if blocks else ""

    def _format_raw_history(self, messages: list[Message]) -> list[str]:
        """Format messages without compression."""
        formatted = []
        for msg in messages[-self.SHORT_HISTORY_THRESHOLD :]:
            role = "User" if msg.role == "user" else "Assistant"
            formatted.append(f"{role}: {msg.text}")
        return formatted

    async def _compress_history(self, messages: list[Message]) -> str:
        """
        Compress long conversation history using Chain-of-Density approach.

        Current implementation: simple extractive summarization.
        """
        if not messages:
            return ""

        key_points = []

        for msg in messages:
            text = msg.text.strip()
            if len(text) > 100:
                sentence_end = text.find(". ")
                if sentence_end > 0:
                    text = text[: sentence_end + 1]
                else:
                    text = text[:100] + "..."

            role_prefix = "User" if msg.role == "user" else "I"
            key_points.append(f"{role_prefix}: {text}")

        compressed = " | ".join(key_points[-10:])
        tokens = self.estimate_tokens(compressed)

        if tokens > self.MAX_COMPRESSED_TOKENS:
            target_chars = self.MAX_COMPRESSED_TOKENS * 4
            compressed = compressed[:target_chars] + "..."
            logger.debug("[CONTEXT_COMPRESSION] Trimmed to %s tokens", self.MAX_COMPRESSED_TOKENS)

        return compressed
