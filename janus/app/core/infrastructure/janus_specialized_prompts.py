from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

# Templates Especializados do Sistema Janus

"""
Templates otimizados para funcionalidades core do Janus:
- Integração de memórias semânticas
- Planejamento de queries ao Knowledge Graph
- Recuperação inteligente de erros
- Compressão de contexto em conversas longas
"""

# ==================== MEMORY INTEGRATION TEMPLATE ====================

MEMORY_INTEGRATION_TEMPLATE = get_prompt_with_fallback("memory_integration")


# ==================== GRAPH QUERY PLANNING TEMPLATE ====================

GRAPH_QUERY_PLANNING_TEMPLATE = get_prompt_with_fallback("graph_query_planning")


# ==================== ERROR RECOVERY TEMPLATE ====================

ERROR_RECOVERY_TEMPLATE = get_prompt_with_fallback("error_recovery")


# ==================== CONTEXT COMPRESSION TEMPLATE ====================

CONTEXT_COMPRESSION_TEMPLATE = get_prompt_with_fallback("context_compression")



# Exportar todos os templates
__all__ = [
    "MEMORY_INTEGRATION_TEMPLATE",
    "GRAPH_QUERY_PLANNING_TEMPLATE",
    "ERROR_RECOVERY_TEMPLATE",
    "CONTEXT_COMPRESSION_TEMPLATE",
]
