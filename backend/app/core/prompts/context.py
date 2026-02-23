"""
Data structures for conversation context in the modular prompt system.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """Represents a single message in conversation history."""

    role: str  # "user" or "assistant"
    text: str
    metadata: dict[str, Any] | None = None


@dataclass
class ConversationContext:
    """
    Encapsulates all contextual information needed for prompt composition.
    """

    history: list[Message]
    current_message: str
    summary: str | None = None
    relevant_memories: str | None = None
    persona: str = "assistant"
    user_preferences: dict[str, Any] | None = None

    def __post_init__(self):
        """Normalize history to Message objects if needed."""
        normalized = []
        for msg in self.history:
            if isinstance(msg, dict):
                normalized.append(
                    Message(
                        role=msg.get("role", "user"),
                        text=msg.get("text", ""),
                        metadata=msg.get("metadata"),
                    )
                )
            elif isinstance(msg, Message):
                normalized.append(msg)
        self.history = normalized

    @property
    def history_length(self) -> int:
        """Total number of messages in history."""
        return len(self.history)

    @property
    def total_tokens_estimate(self) -> int:
        """Rough estimate of tokens in history (chars / 4)."""
        total_chars = sum(len(msg.text) for msg in self.history)
        total_chars += len(self.current_message)
        if self.summary:
            total_chars += len(self.summary)
        if self.relevant_memories:
            total_chars += len(self.relevant_memories)
        return total_chars // 4
