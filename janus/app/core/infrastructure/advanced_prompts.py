# Prompts Avançados do Sistema Janus
# Este arquivo contém templates avançados para cenários específicos que requerem raciocínio complexo.

from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

# ## Chain-of-Thought Reasoning Template
CHAIN_OF_THOUGHT_TEMPLATE = get_prompt_with_fallback("capability_chain_of_thought")

# ## Self-Correction Template
SELF_CORRECTION_TEMPLATE = get_prompt_with_fallback("capability_self_correction")

# ## Multi-Agent Coordination Template
MULTI_AGENT_COORDINATION_TEMPLATE = get_prompt_with_fallback("capability_multi_agent_coordination")

# ## Code Review Template
CODE_REVIEW_TEMPLATE = get_prompt_with_fallback("capability_code_review")

# ## Hypothesis-Driven Problem Solving
HYPOTHESIS_DRIVEN_DEBUGGING_TEMPLATE = get_prompt_with_fallback("capability_hypothesis_debugging")
