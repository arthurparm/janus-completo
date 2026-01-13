"""
Context Compression Module - Intelligent history summarization.
Uses Chain-of-Density approach to compress long conversations.
"""

import logging

from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.types import IntentType

logger = logging.getLogger(__name__)


class ContextCompressionModule(PromptModule):
    """
    Compresses conversation history to reduce token consumption.
    - Short histories (≤3 messages): No compression
    - Long histories: Chain-of-Density summarization
    """

    SHORT_HISTORY_THRESHOLD = 3  # Messages
    MAX_COMPRESSED_TOKENS = 200  # Target size after compression

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

        lines = []

        # Add summary if available
        if context.summary:
            lines.append("\n**Previous Context Summary:**")
            lines.append(context.summary)

        # Add relevant memories
        if context.relevant_memories:
            lines.append("\n**Relevant Facts from Memory:**")
            lines.append(context.relevant_memories)
            lines.append("(Use these facts to personalize your response if appropriate)\n")

        # Handle conversation history
        if context.history:
            if context.history_length <= self.SHORT_HISTORY_THRESHOLD:
                # Short history - include verbatim
                lines.append("\n**Recent Conversation:**")
                lines.extend(self._format_raw_history(context.history))
            else:
                # Long history - compress
                compressed = await self._compress_history(context.history)
                lines.append("\n**Compressed Conversation Context:**")
                lines.append(compressed)

        return "\n".join(lines) if lines else ""

    def _format_raw_history(self, messages: list[Message]) -> list[str]:
        """Format messages without compression."""
        formatted = []
        for msg in messages[-self.SHORT_HISTORY_THRESHOLD :]:  # Last N messages only
            role = "User" if msg.role == "user" else "Assistant"
            formatted.append(f"{role}: {msg.text}")
        return formatted

    async def _compress_history(self, messages: list[Message]) -> str:
        """
        Compress long conversation history using Chain-of-Density approach.

        Current implementation: Simple extractive summarization
        TODO: Integrate LLM-based compression for better quality
        """
        if not messages:
            return ""

        # Extract key information from each message
        key_points = []

        for msg in messages:
            # Extract first sentence or first 100 chars
            text = msg.text.strip()
            if len(text) > 100:
                # Find first sentence
                sentence_end = text.find(". ")
                if sentence_end > 0:
                    text = text[: sentence_end + 1]
                else:
                    text = text[:100] + "..."

            role_prefix = "User" if msg.role == "user" else "I"
            key_points.append(f"{role_prefix}: {text}")

        # Join and ensure under token limit
        compressed = " | ".join(key_points[-10:])  # Last 10 message summaries

        tokens = self.estimate_tokens(compressed)

        if tokens > self.MAX_COMPRESSED_TOKENS:
            # Too long, trim further
            target_chars = self.MAX_COMPRESSED_TOKENS * 4  # Convert tokens to chars
            compressed = compressed[:target_chars] + "..."
            logger.debug(f"[CONTEXT_COMPRESSION] Trimmed to {self.MAX_COMPRESSED_TOKENS} tokens")

        return compressed
