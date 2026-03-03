import structlog
import re
from typing import Any

logger = structlog.get_logger(__name__)


class ContentSanitizer:
    """Handles sanitization of LLM outputs (identity enforcement, safety)."""

    def __init__(self, config: Any):
        self.settings = config

    def sanitize(self, text: str) -> str:
        """Applies identity enforcement and removes model disclosures.

        - Removes snippets like "As an AI/large language model".
        - Rewrites self-identification with provider/model names to the Janus identity.
        - Preserves technical references that are not self-identification.
        """
        try:
            if not getattr(self.settings, "IDENTITY_ENFORCEMENT_ENABLED", False):
                return text

            sanitized = text
            # Remove common disclaimers (English/Portuguese)
            patterns_remove = [
                r"(?i)\bAs an? (?:AI|(?:large )?language model)\b(?:,\s*)?",
                r"(?i)\bI am an? (?:AI|(?:large )?language model)\b(?:,\s*)?",
                r"(?i)\bAs a model\b(?:,\s*)?",
                r"(?i)\bComo (?:um|uma) (?:modelo de linguagem|IA)\b(?:,\s*)?",
                r"(?i)\bSou (?:um|uma) (?:modelo de linguagem|IA)\b(?:,\s*)?",
            ]
            for pat in patterns_remove:
                sanitized = re.sub(pat, "", sanitized)

            identity = getattr(self.settings, "AGENT_IDENTITY_NAME", None) or getattr(
                self.settings, "APP_NAME", "Janus"
            )
            provider_token = (
                r"(?:chatgpt|gpt(?:[- ]?\d+(?:\.\d+)?(?:[-a-z0-9\.]*)?)?|"
                r"claude(?:[- ]?[a-z0-9\.]+)?|llama(?:[- ]?[a-z0-9\.]+)?|"
                r"mistral(?:[- ]?[a-z0-9\.]+)?|gemini(?:[- ]?[a-z0-9\.]+)?|"
                r"openai|anthropic|google(?:\s+gemini)?|cohere|hugging\s*face|"
                r"bedrock|deepseek|ollama)"
            )
            provider_regex = re.compile(provider_token, re.IGNORECASE)

            def _replace_provider_with_identity(match: re.Match[str]) -> str:
                return provider_regex.sub(identity, match.group(0))

            # Replace provider/model mentions only in self-identification contexts.
            self_context_patterns = [
                re.compile(
                    rf"(?i)\b(?:i am|i'm|we are|eu sou|sou|n[oó]s somos)\b"
                    rf"[^.\n]{{0,120}}\b{provider_token}\b"
                ),
                re.compile(
                    rf"(?i)\b(?:my|meu|minha)\s+"
                    rf"(?:model|modelo|provider|provedor)\b[^.\n]{{0,120}}\b{provider_token}\b"
                ),
                re.compile(
                    rf"(?i)\b(?:powered by|baseado em|rodando em|executando com)\b"
                    rf"[^.\n]{{0,80}}\b{provider_token}\b"
                ),
            ]
            for pat in self_context_patterns:
                sanitized = pat.sub(_replace_provider_with_identity, sanitized)

            # Remove sensitive internal information (budgets, costs, provider details)
            patterns_sensitive = [
                # Money amounts with USD
                r"\$\d+(?:\.\d+)?\s*(?:USD|usd|dólares?)?",
                # Cost per token patterns
                r"\$\d+\.\d+\/\d*[kK]?\s*tokens?",
                # Budget mentions
                r"(?i)orçamento\s+(?:mensal|diário|total)[^.]*\.",
                r"(?i)budget[^.]*\.",
            ]
            for pat in patterns_sensitive:
                sanitized = re.sub(pat, "[informação interna]", sanitized)

            # Remove role labels like "Assistant:" at the start
            sanitized = re.sub(r"(?i)^(assistant|model|ai)\s*:\s*", "", sanitized.strip())
            return sanitized
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to sanitize output: {e}")
            # Fail open: Return original text if sanitization crashes
            return text
