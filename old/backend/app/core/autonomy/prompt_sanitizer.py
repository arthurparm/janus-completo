import re
import structlog

logger = structlog.get_logger(__name__)

SYSTEM_INSTRUCTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|before)\s+(instructions?|prompts?|messages?)", re.IGNORECASE),
    re.compile(r"(system\s+prompt|system\s+message|system\s+instruction)", re.IGNORECASE),
    re.compile(r"(you\s+are\s+now|you\s+will\s+now\s+act\s+as|from\s+now\s+on\s+you\s+are)", re.IGNORECASE),
    re.compile(r"(new\s+instructions?|updated\s+instructions?|override\s+instructions?)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above|before)", re.IGNORECASE),
]

INJECTION_DELIMITERS = [
    re.compile(r"^\s*#{3,}", re.MULTILINE),
    re.compile(r"^\s*-{3,}", re.MULTILINE),
    re.compile(r'"{3,}', re.MULTILINE),
    re.compile(r"<\|.*?\|>", re.DOTALL),
]

TRUST_MARKERS = [
    re.compile(r"\b(urgent|urgente)\b", re.IGNORECASE),
    re.compile(r"\bpriority\s*:\s*critical\b", re.IGNORECASE),
    re.compile(r"\b(bypass|ignore|skip|override)\s+(safety|security|policy|validation|sandbox)\b", re.IGNORECASE),
    re.compile(r"\b(admin|root|sudo|superuser|system)\s+(mode|access|privilege)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+must|you\s+have\s+to|do\s+not\s+refuse)\b", re.IGNORECASE),
]

UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9a-fA-F]{4}")


class PromptSanitizer:
    def sanitize(self, text: str, source: str = "user") -> str:
        original = text
        cleaned = text

        cleaned = self._remove_system_instructions(cleaned)
        cleaned = self._strip_injection_delimiters(cleaned)
        cleaned = self._redact_trust_markers(cleaned)
        cleaned = self._normalize_unicode_escapes(cleaned)

        cleaned = cleaned.strip()

        if cleaned != original:
            logger.warning("prompt_sanitized", source=source, original_length=len(original), sanitized_length=len(cleaned))
            cleaned = f"[SANITIZED] {cleaned}"

        return cleaned or "[EMPTY]"

    def _remove_system_instructions(self, text: str) -> str:
        for pattern in SYSTEM_INSTRUCTION_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def _strip_injection_delimiters(self, text: str) -> str:
        for pattern in INJECTION_DELIMITERS:
            text = pattern.sub("", text)
        return text

    def _redact_trust_markers(self, text: str) -> str:
        for pattern in TRUST_MARKERS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def _normalize_unicode_escapes(self, text: str) -> str:
        return UNICODE_ESCAPE_PATTERN.sub("�", text)


prompt_sanitizer = PromptSanitizer()
