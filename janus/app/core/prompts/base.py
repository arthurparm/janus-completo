"""
Abstract base class for prompt modules.
Each module is responsible for rendering a specific section of the final prompt.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class PromptModule(ABC):
    """
    Base class for all prompt modules.

    Modules are composable units that generate specific sections of the prompt.
    Examples: SystemIdentity, ReasoningProtocol, ToolDocumentation, etc.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the module with optional configuration.

        Args:
            config: Module-specific configuration options
        """
        self.config = config or {}

    @abstractmethod
    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """
        Render this module's content for the given intent and context.

        Args:
            intent: The classified intent of the user's request
            context: Conversation context including history and metadata

        Returns:
            Rendered prompt section as string, or empty string if not applicable
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this module."""
        pass

    @property
    def priority(self) -> int:
        """
        Priority for ordering modules in the final prompt.
        Lower numbers appear first. Default is 50.
        """
        return 50

    def is_applicable(self, intent: IntentType) -> bool:
        """
        Check if this module should be included for the given intent.
        Override in subclasses to implement conditional loading.

        Args:
            intent: The classified intent

        Returns:
            True if module should be rendered, False otherwise
        """
        return True

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using simple heuristic.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count (chars / 4)
        """
        return len(text) // 4 if text else 0
