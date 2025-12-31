import re
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class ContentSanitizer:
    """Handles sanitization of LLM outputs (identity enforcement, safety)."""

    def __init__(self, config: Any):
        self.settings = config

    def sanitize(self, text: str) -> str:
        """Applies identity enforcement and removes model disclosures.

        - Removes snippets like "As an AI/large language model".
        - Replaces model/provider names with "Janus".
        """
        try:
            if not getattr(self.settings, "IDENTITY_ENFORCEMENT_ENABLED", False):
                return text
            
            sanitized = text
            # Remove common disclaimers (English/Portuguese)
            patterns_remove = [
                r"(?i)\bAs an? (?:AI|(?:large )?language model)[^\.\n]*[\.\n]?",
                r"(?i)\bI am an? (?:AI|(?:large )?language model)[^\.\n]*[\.\n]?",
                r"(?i)\bAs a model[^\.\n]*[\.\n]?",
                r"(?i)\bComo (?:um|uma) (?:modelo de linguagem|IA)[^\.\n]*[\.\n]?",
                r"(?i)\bSou (?:um|uma) (?:modelo de linguagem|IA)[^\.\n]*[\.\n]?",
            ]
            for pat in patterns_remove:
                sanitized = re.sub(pat, "", sanitized)

            # Replace model/provider names with identity
            identity = getattr(self.settings, "AGENT_IDENTITY_NAME", None) or getattr(self.settings, "APP_NAME", "Janus")
            patterns_replace = [
                r"(?i)\bGPT[- ]?\d(?:\.\d)?\b",
                r"(?i)\bChatGPT\b",
                r"(?i)\bClaude(?:[- ]?\d+)?\b",
                r"(?i)\bLlama(?:[- ]?\d+)?\b",
                r"(?i)\bMistral(?:[- ]?\d+)?\b",
                r"(?i)\bGemini\b",
                r"(?i)\bOpenAI\b",
                r"(?i)\bAnthropic\b",
                r"(?i)\bGoogle(?:\s+Gemini)?\b",
                r"(?i)\bCohere\b",
                r"(?i)\bHugging\s*Face\b",
                r"(?i)\bBedrock\b",
            ]
            for pat in patterns_replace:
                sanitized = re.sub(pat, identity, sanitized)

            # Remove role labels like "Assistant:" at the start
            sanitized = re.sub(r"(?i)^(assistant|model|ai)\s*:\s*", "", sanitized.strip())
            return sanitized
        except Exception as e:
            logger.warning(f"Failed to sanitize output: {e}")
            # Fail open: Return original text if sanitization crashes
            return text
