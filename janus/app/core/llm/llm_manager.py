"""
Módulo de compatibilidade para LLM Manager.
A lógica foi decomposta em sub-módulos: types, pricing, resilience, factory, router, client.
Este arquivo re-exporta os símbolos públicos para manter a compatibilidade.
"""

from .types import (
    ModelRole, 
    ModelPriority, 
    CachedLLM, 
    ProviderPricing, 
    ProviderStats, 
    ModelStats
)
from .pricing import (
    LLM_PROVIDER_SPEND_USD, 
    LLM_PROVIDER_BUDGET_REMAINING, 
    LLM_TENANT_SPEND_USD, 
    LLM_COST_DEVIATION_USD, 
    LLM_EXPECTED_KTOKENS_GAUGE,
    _provider_stats,
    _model_stats,
    _provider_pricing,
    _provider_budgets_usd,
    _provider_spend_usd,
    _model_penalty_factors,
    _expected_k_ema_by_role,
    _tenant_user_daily_budget_usd,
    _tenant_project_daily_budget_usd,
    _tenant_user_spend_usd,
    _tenant_project_spend_usd,
    _budget_remaining,
    _budget_allows,
    _get_model_pricing,
    _tenant_budget_remaining,
    _register_tenant_spend,
)
from .resilience import (
    invalidate_cache, 
    LLM_POOL_SIZE, 
    LLM_POOL_HITS, 
    LLM_POOL_MISSES, 
    LLM_POOL_EVICTIONS, 
    LLM_POOL_WARMS, 
    _llm_pool, 
    _provider_circuit_breakers,
    _circuit_closed,
    _get_from_pool,
    _add_to_pool,
    _pool_key
)
from .factory import (
    warm_llm_pool,
    _get_executor,
    _get_openai_client,
    _validate_gemini_key,
    _validate_openai_key,
    _health_check_ollama,
    _infer_provider,
    _infer_model_name
)
from .router import (
    get_llm, 
    LLM_ROUTER_COUNTER, 
    LLM_SELECTION_SCORE, 
    LLM_MODEL_SELECTION_SCORE, 
    LLM_EXPECTED_COST_USD, 
    LLM_EXPLORATION_DECISIONS,
    _normalize
)
from .client import (
    LLMClient, 
    get_llm_client, 
    LLM_REQUESTS, 
    LLM_LATENCY, 
    LLM_TOKENS
)
