"""
Intent classification for routing to appropriate prompt modules.
Extracted from prompt_builder_service.py to separate logic from prompt content.
"""

import logging
from typing import Any

from app.core.prompts.types import IntentType

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies user messages into intent types for prompt module selection.
    Uses keyword-based classification with confidence scoring.
    """

    # Keyword mappings for each intent type
    INTENT_KEYWORDS = {
        IntentType.TOOL_CREATION: [
            "tool",
            "ferramenta",
            "capability",
            "capacidade",
            "habilidade",
            "ability",
            "crie uma ferramenta",
            "create a tool",
        ],
        IntentType.SCRIPT_GENERATION: [
            "script",
            "file",
            "arquivo",
            "código",
            "write a script",
            "escreva um script",
            "generate code",
            "write code",
        ],
        IntentType.CODE_REVIEW: [
            "review",
            "revisar",
            "code review",
            "check code",
            "verificar código",
            "analyze code",
        ],
        IntentType.DEBUGGING: [
            "debug",
            "depurar",
            "error",
            "erro",
            "bug",
            "fix",
            "corrigir",
            "not working",
            "não funciona",
        ],
        IntentType.DOCUMENTATION: [
            "document",
            "documentar",
            "docs",
            "readme",
            "explain how",
            "como usar",
        ],
        IntentType.CAPABILITIES_QUERY: [
            "what can you do",
            "o que você pode fazer",
            "capabilities",
            "capacidades",
            "features",
            "funcionalidades",
            "ferramentas disponíveis",
            "available tools",
        ],
        IntentType.QUESTION: [
            "?",
            "como",
            "what",
            "why",
            "quando",
            "where",
            "quem",
            "qual",
        ],
    }

    def classify(self, message: str) -> IntentType:
        """
        Classify user message into an intent type.

        Args:
            message: User's message text

        Returns:
            Classified intent type
        """
        message_lower = message.lower()

        # Check each intent type by keyword matching
        intent_scores: dict[IntentType, int] = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in message_lower)
            if score > 0:
                intent_scores[intent] = score

        # Return intent with highest score
        if intent_scores:
            classified = max(intent_scores, key=intent_scores.get)
            confidence = self._calculate_confidence(intent_scores[classified], len(message))

            logger.info(
                f"[INTENT_CLASSIFICATION] Classified as {classified.value} "
                f"(confidence: {confidence:.2f})"
            )
            return classified

        # Default to casual chat if no strong signals
        logger.info("[INTENT_CLASSIFICATION] No strong signals, defaulting to CASUAL_CHAT")
        return IntentType.CASUAL_CHAT

    def get_confidence(self, message: str, intent: IntentType) -> float:
        """
        Calculate confidence score for a given intent classification.

        Args:
            message: User's message text
            intent: The classified intent

        Returns:
            Confidence score between 0.0 and 1.0
        """
        message_lower = message.lower()
        keywords = self.INTENT_KEYWORDS.get(intent, [])

        keyword_hits = sum(1 for kw in keywords if kw.lower() in message_lower)
        return self._calculate_confidence(keyword_hits, len(message))

    def _calculate_confidence(self, keyword_hits: int, message_length: int) -> float:
        """
        Calculate confidence score based on keyword hits and message length.

        More hits = higher confidence
        Longer messages with few hits = lower confidence

        Args:
            keyword_hits: Number of matching keywords
            message_length: Length of message in characters

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if keyword_hits == 0:
            return 0.0

        # Base confidence from keyword hits
        base_confidence = min(keyword_hits * 0.3, 0.9)

        # Adjust for message length (penalize if message is long but few hits)
        if message_length > 100:
            length_penalty = 1 - (message_length / 1000)  # Small penalty for length
            return max(base_confidence * length_penalty, 0.1)

        return base_confidence

    def is_tool_request(self, message: str) -> bool:
        """Check if message is requesting tool creation (backward compatibility)."""
        return self.classify(message) == IntentType.TOOL_CREATION

    def is_script_request(self, message: str) -> bool:
        """Check if message is requesting script generation (backward compatibility)."""
        return self.classify(message) == IntentType.SCRIPT_GENERATION

    def is_capabilities_query(self, message: str) -> bool:
        """Check if message is asking about capabilities (backward compatibility)."""
        return self.classify(message) == IntentType.CAPABILITIES_QUERY
