"""Static prompt support retained after permanent removal of code self-evolution."""

from app.core.evolution.prompts import (
    TOOL_GENERATION_PROMPT,
    TOOL_SPECIFICATION_PROMPT,
    tool_validation_prompt,
)

__all__ = ["TOOL_GENERATION_PROMPT", "TOOL_SPECIFICATION_PROMPT", "tool_validation_prompt"]
