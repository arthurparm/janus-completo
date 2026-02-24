import os
import re

_CITATION_REQUIRED_PATTERNS = (
    r"\bcodigo\b",
    r"\bcode\b",
    r"\bfuncao\b",
    r"\bfunction\b",
    r"\bclasse\b",
    r"\bclass\b",
    r"\barquivo\b",
    r"\bfile\b",
    r"\bdocumentacao\b",
    r"\bdocumentation\b",
    r"\bdocs?\b",
    r"\breadme\b",
    r"\bapi\b",
    r"\bendpoint\b",
    r"\.py\b",
    r"\.ts\b",
    r"\.js\b",
)


def requires_mandatory_citations(message: str) -> bool:
    text = (message or "").lower()
    return any(re.search(pattern, text) for pattern in _CITATION_REQUIRED_PATTERNS)


def confidence_confirmation_threshold() -> float:
    raw = os.getenv("CHAT_CONFIDENCE_CONFIRMATION_THRESHOLD", "0.65").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.65


def confidence_band(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"
