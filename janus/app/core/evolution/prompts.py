from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

# Nota: Estas constantes são definidas como strings vazias inicialmente
# e devem ser carregadas de forma assíncrona durante a inicialização.

TOOL_SPECIFICATION_PROMPT = ""

TOOL_GENERATION_PROMPT = ""

tool_validation_prompt = ""


async def load_evolution_prompts():
    """Carrega os prompts de evolução de forma assíncrona."""
    global TOOL_SPECIFICATION_PROMPT
    global TOOL_GENERATION_PROMPT
    global tool_validation_prompt

    TOOL_SPECIFICATION_PROMPT = await get_prompt_with_fallback("tool_specification")
    TOOL_GENERATION_PROMPT = await get_prompt_with_fallback("tool_generation")
    tool_validation_prompt = await get_prompt_with_fallback("tool_validation")
