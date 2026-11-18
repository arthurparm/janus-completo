"""Shared policy for deciding when chat answers require traceable citations.

This module is intentionally free of retrieval, transport, and persistence concerns.
REST, SSE, study, and citation collection must all consult this source of truth.
"""

from __future__ import annotations

import re

_CITATION_REQUIRED_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
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
)


def requires_mandatory_citations(message: str) -> bool:
    """Return whether ``message`` requires a source-backed answer.

    The contract lower-cases input without accent folding or fuzzy expansion,
    keeping classification deterministic across every caller.
    """

    text = (message or "").lower()
    return any(pattern.search(text) for pattern in _CITATION_REQUIRED_PATTERNS)
