# Prompts Avançados do Sistema Janus
# Este arquivo contém templates avançados para cenários específicos que requerem raciocínio complexo.

from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

# Nota: Estas constantes são definidas como strings vazias inicialmente
# e devem ser carregadas de forma assíncrona durante a inicialização ou uso.
# TODO: Refatorar o uso destas constantes para chamadas assíncronas diretas.

# ## Chain-of-Thought Reasoning Template
CHAIN_OF_THOUGHT_TEMPLATE = ""

# ## Self-Correction Template
SELF_CORRECTION_TEMPLATE = ""

# ## Multi-Agent Coordination Template
MULTI_AGENT_COORDINATION_TEMPLATE = ""

# ## Code Review Template
CODE_REVIEW_TEMPLATE = ""

# ## Hypothesis-Driven Problem Solving
HYPOTHESIS_DRIVEN_DEBUGGING_TEMPLATE = ""

async def load_advanced_prompts():
    """Carrega os prompts avançados de forma assíncrona."""
    global CHAIN_OF_THOUGHT_TEMPLATE
    global SELF_CORRECTION_TEMPLATE
    global MULTI_AGENT_COORDINATION_TEMPLATE
    global CODE_REVIEW_TEMPLATE
    global HYPOTHESIS_DRIVEN_DEBUGGING_TEMPLATE

    CHAIN_OF_THOUGHT_TEMPLATE = await get_prompt_with_fallback("capability_chain_of_thought")
    SELF_CORRECTION_TEMPLATE = await get_prompt_with_fallback("capability_self_correction")
    MULTI_AGENT_COORDINATION_TEMPLATE = await get_prompt_with_fallback("capability_multi_agent_coordination")
    CODE_REVIEW_TEMPLATE = await get_prompt_with_fallback("capability_code_review")
    HYPOTHESIS_DRIVEN_DEBUGGING_TEMPLATE = await get_prompt_with_fallback("capability_hypothesis_debugging")
