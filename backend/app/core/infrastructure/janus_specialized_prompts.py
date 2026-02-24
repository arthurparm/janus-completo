from app.core.infrastructure.prompt_loader import get_prompt

# Templates Especializados do Sistema Janus

"""
Templates otimizados para funcionalidades core do Janus:
- Integração de memórias semânticas
- Planejamento de queries ao Knowledge Graph
- Recuperação inteligente de erros
- Compressão de contexto em conversas longas
"""

# Nota: Estas constantes são definidas como strings vazias inicialmente
# e devem ser carregadas de forma assíncrona durante a inicialização.

# ==================== MEMORY INTEGRATION TEMPLATE ====================

MEMORY_INTEGRATION_TEMPLATE = ""


# ==================== GRAPH QUERY PLANNING TEMPLATE ====================

GRAPH_QUERY_PLANNING_TEMPLATE = ""


# ==================== ERROR RECOVERY TEMPLATE ====================

ERROR_RECOVERY_TEMPLATE = ""


# ==================== CONTEXT COMPRESSION TEMPLATE ====================

CONTEXT_COMPRESSION_TEMPLATE = ""


async def load_specialized_prompts():
    """Carrega os templates especializados de forma assíncrona."""
    global MEMORY_INTEGRATION_TEMPLATE
    global GRAPH_QUERY_PLANNING_TEMPLATE
    global ERROR_RECOVERY_TEMPLATE
    global CONTEXT_COMPRESSION_TEMPLATE

    MEMORY_INTEGRATION_TEMPLATE = await get_prompt("memory_integration")
    GRAPH_QUERY_PLANNING_TEMPLATE = await get_prompt("graph_query_planning")
    ERROR_RECOVERY_TEMPLATE = await get_prompt("error_recovery")
    CONTEXT_COMPRESSION_TEMPLATE = await get_prompt("context_compression")


# Exportar todos os templates
__all__ = [
    "MEMORY_INTEGRATION_TEMPLATE",
    "GRAPH_QUERY_PLANNING_TEMPLATE",
    "ERROR_RECOVERY_TEMPLATE",
    "CONTEXT_COMPRESSION_TEMPLATE",
    "load_specialized_prompts",
]
