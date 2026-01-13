from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

TOOL_SPECIFICATION_PROMPT = get_prompt_with_fallback("tool_specification")

TOOL_GENERATION_PROMPT = get_prompt_with_fallback("tool_generation")

tool_validation_prompt = get_prompt_with_fallback("tool_validation")
