from typing import Dict, Any, Optional
from datetime import datetime
from prometheus_client import Counter, Gauge

from app.config import settings
from .types import ProviderPricing, ProviderStats, ModelStats

# Metrics
LLM_PROVIDER_SPEND_USD = Counter(
    "llm_provider_spend_usd_total",
    "Gasto acumulado em USD por provedor",
    ["provider", "category"],
)
LLM_PROVIDER_BUDGET_REMAINING = Gauge(
    "llm_provider_budget_remaining_usd",
    "Orçamento restante em USD por provedor",
    ["provider"],
)
LLM_TENANT_SPEND_USD = Counter(
    "llm_tenant_spend_usd_total",
    "Gasto acumulado em USD por tenant",
    ["kind", "id"],
)
LLM_COST_DEVIATION_USD = Gauge(
    "llm_cost_deviation_usd",
    "Desvio do custo real vs estimado (USD) por candidato",
    ["provider", "model", "role"],
)
LLM_EXPECTED_KTOKENS_GAUGE = Gauge(
    "llm_expected_ktokens_by_role",
    "EMA de expected_k (ktokens) por papel",
    ["role"],
)

# State
_provider_stats: Dict[str, ProviderStats] = {
    "openai": ProviderStats(),
    "google_gemini": ProviderStats(),
    "ollama": ProviderStats(),
}

_model_stats: Dict[str, Dict[str, ModelStats]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
}

# Pricing por provedor (valores padrão via settings; Ollama ~ 0)
_provider_pricing: Dict[str, ProviderPricing] = {
    "openai": ProviderPricing(
        input_per_1k_usd=settings.OPENAI_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.OPENAI_COST_PER_1K_OUTPUT_USD,
    ),
    "google_gemini": ProviderPricing(
        input_per_1k_usd=settings.GEMINI_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.GEMINI_COST_PER_1K_OUTPUT_USD,
    ),
    "ollama": ProviderPricing(
        input_per_1k_usd=settings.OLLAMA_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.OLLAMA_COST_PER_1K_OUTPUT_USD,
    ),
}

# Orçamentos mensais por provedor
_provider_budgets_usd: Dict[str, float] = {
    "openai": settings.OPENAI_MONTHLY_BUDGET_USD,
    "google_gemini": settings.GEMINI_MONTHLY_BUDGET_USD,
    "ollama": settings.OLLAMA_MONTHLY_BUDGET_USD,
}

# Rastreamento de gastos acumulados
_provider_spend_usd: Dict[str, float] = {"openai": 0.0, "google_gemini": 0.0, "ollama": 0.0}

# Fatores de penalização por modelo (>=1.0). Quanto maior, menos preferido.
_model_penalty_factors: Dict[str, Dict[str, float]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
}

# EMA dinâmica de expected_k por papel (ktokens). Inicializa a partir das configurações.
_expected_k_ema_by_role: Dict[str, float] = {}
for _role_key, _k in getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {}).items():
    try:
        _expected_k_ema_by_role[_role_key] = float(_k)
    except Exception:
        _expected_k_ema_by_role[_role_key] = 2.0

try:
    for rk, val in _expected_k_ema_by_role.items():
        LLM_EXPECTED_KTOKENS_GAUGE.labels(role=rk).set(val)
except Exception:
    pass


# Orçamentos diários multitenant (USD)
_tenant_user_daily_budget_usd: float = getattr(settings, "TENANT_USER_DAILY_BUDGET_USD", 0.0) or 0.0
_tenant_project_daily_budget_usd: float = getattr(settings, "TENANT_PROJECT_DAILY_BUDGET_USD", 0.0) or 0.0

# Rastreamento de gastos por usuário/projeto (reset diário)
_tenant_user_spend_usd: Dict[str, Dict[str, Any]] = {}
_tenant_project_spend_usd: Dict[str, Dict[str, Any]] = {}


def _today_str() -> str:
    try:
        return datetime.utcnow().strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _budget_remaining(provider: str) -> float:
    budget = _provider_budgets_usd.get(provider, 0.0)
    spend = _provider_spend_usd.get(provider, 0.0)
    return max(0.0, budget - spend)


def _budget_allows(provider: str) -> bool:
    # Orçamento 0.0 implica sem custo/sem controle (ex.: Ollama)
    budget = _provider_budgets_usd.get(provider, 0.0)
    if budget <= 0.0:
        return True
    return _budget_remaining(provider) > 0.0


def _get_model_pricing(provider: str, model_name: str) -> ProviderPricing:
    try:
        if provider == "openai":
            mp = settings.OPENAI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(mp.get("input_per_1k_usd", settings.OPENAI_COST_PER_1K_INPUT_USD),
                                       mp.get("output_per_1k_usd", settings.OPENAI_COST_PER_1K_OUTPUT_USD))
            return ProviderPricing(settings.OPENAI_COST_PER_1K_INPUT_USD, settings.OPENAI_COST_PER_1K_OUTPUT_USD)
        if provider == "google_gemini":
            mp = settings.GEMINI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(mp.get("input_per_1k_usd", settings.GEMINI_COST_PER_1K_INPUT_USD),
                                       mp.get("output_per_1k_usd", settings.GEMINI_COST_PER_1K_OUTPUT_USD))
            return ProviderPricing(settings.GEMINI_COST_PER_1K_INPUT_USD, settings.GEMINI_COST_PER_1K_OUTPUT_USD)
        # ollama
        return ProviderPricing(settings.OLLAMA_COST_PER_1K_INPUT_USD, settings.OLLAMA_COST_PER_1K_OUTPUT_USD)
    except Exception:
        return ProviderPricing(0.0, 0.0)


def _tenant_budget_remaining(kind: str, id_: Optional[str]) -> float:
    if not id_:
        return float("inf")
    today = _today_str()
    if kind == "user":
        budget = _tenant_user_daily_budget_usd
        entry = _tenant_user_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_user_spend_usd[id_]
        return max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0)) if budget > 0 else float("inf")
    else:  # project
        budget = _tenant_project_daily_budget_usd
        entry = _tenant_project_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_project_spend_usd[id_]
        return max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0)) if budget > 0 else float("inf")


def _register_tenant_spend(kind: str, id_: Optional[str], cost_usd: float):
    if not id_:
        return
    today = _today_str()
    cost_usd = max(0.0, float(cost_usd))
    if kind == "user":
        entry = _tenant_user_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
        _tenant_user_spend_usd[id_]["usd"] = (_tenant_user_spend_usd[id_]["usd"] or 0.0) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="user", id=id_).inc(cost_usd)
        except Exception:
            pass
    else:
        entry = _tenant_project_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
        _tenant_project_spend_usd[id_]["usd"] = (_tenant_project_spend_usd[id_]["usd"] or 0.0) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="project", id=id_).inc(cost_usd)
        except Exception:
            pass
