import asyncio
from datetime import datetime
from typing import Any

from prometheus_client import Counter, Gauge

from app.config import settings
from app.core.infrastructure.redis_usage_tracker import get_redis_usage_tracker

from .types import ModelStats, ProviderPricing, ProviderStats

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
_provider_stats: dict[str, ProviderStats] = {
    "openai": ProviderStats(),
    "google_gemini": ProviderStats(),
    "ollama": ProviderStats(),
    "deepseek": ProviderStats(),
    "xai": ProviderStats(),
}

_model_stats: dict[str, dict[str, ModelStats]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
    "deepseek": {},
    "xai": {},
}

# Pricing por provedor (valores padrão via settings; Ollama ~ 0)
_provider_pricing: dict[str, ProviderPricing] = {
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
    "deepseek": ProviderPricing(
        input_per_1k_usd=settings.DEEPSEEK_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.DEEPSEEK_COST_PER_1K_OUTPUT_USD,
        cache_read_per_1k_usd=settings.DEEPSEEK_COST_PER_1K_CACHE_READ_USD,
    ),
    "xai": ProviderPricing(
        input_per_1k_usd=settings.XAI_COST_PER_1K_INPUT_USD,
        output_per_1k_usd=settings.XAI_COST_PER_1K_OUTPUT_USD,
    ),
}

# Orçamentos mensais por provedor
_provider_budgets_usd: dict[str, float] = {
    "openai": settings.OPENAI_MONTHLY_BUDGET_USD,
    "google_gemini": settings.GEMINI_MONTHLY_BUDGET_USD,
    "ollama": settings.OLLAMA_MONTHLY_BUDGET_USD,
    "deepseek": settings.DEEPSEEK_MONTHLY_BUDGET_USD,
    "xai": settings.XAI_MONTHLY_BUDGET_USD,
}

# Rastreamento de gastos acumulados
_provider_spend_usd: dict[str, float] = {
    "openai": 0.0,
    "google_gemini": 0.0,
    "ollama": 0.0,
    "deepseek": 0.0,
    "xai": 0.0,
}

# Fatores de penalização por modelo (>=1.0). Quanto maior, menos preferido.
_model_penalty_factors: dict[str, dict[str, float]] = {
    "openai": {},
    "google_gemini": {},
    "ollama": {},
    "deepseek": {},
    "xai": {},
}

# EMA dinâmica de expected_k por papel (ktokens). Inicializa a partir das configurações.
_expected_k_ema_by_role: dict[str, float] = {}
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
_tenant_project_daily_budget_usd: float = (
    getattr(settings, "TENANT_PROJECT_DAILY_BUDGET_USD", 0.0) or 0.0
)

# Rastreamento de gastos por usuário/projeto (reset diário)
_tenant_user_spend_usd: dict[str, dict[str, Any]] = {}
_tenant_project_spend_usd: dict[str, dict[str, Any]] = {}


def _today_str() -> str:
    try:
        return datetime.utcnow().strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


async def _budget_remaining(provider: str) -> float:
    if provider not in _provider_budgets_usd:
        return float("inf")
    budget = _provider_budgets_usd.get(provider, 0.0)
    if budget <= 0.0:
        return float("inf")
    tracker = None
    try:
        tracker = get_redis_usage_tracker()
    except Exception:
        tracker = None
    spend = _provider_spend_usd.get(provider, 0.0)
    if tracker is not None:
        try:
            spend = await tracker.get_provider_spend(provider)
            _provider_spend_usd[provider] = spend
        except Exception:
            spend = _provider_spend_usd.get(provider, 0.0)
    return max(0.0, budget - spend)


async def _budget_allows(provider: str) -> bool:
    # Orçamento 0.0 implica sem custo/sem controle (ex.: Ollama)
    budget = _provider_budgets_usd.get(provider, 0.0)
    if budget <= 0.0:
        return True
    rem = await _budget_remaining(provider)
    return rem > 0.0


async def is_total_budget_threshold_exceeded() -> bool:
    """
    Check if total cloud spending has exceeded the configured threshold.
    Returns True if spending >= BUDGET_THRESHOLD_PERCENT * total_budget.
    Used for Dynamic Budget Guardrails.
    """
    # Only consider cloud providers with positive budgets
    cloud_providers = ["openai", "google_gemini", "deepseek", "xai"]

    total_budget = sum(_provider_budgets_usd.get(p, 0.0) for p in cloud_providers)

    # Need to fetch latest spend for accuracy
    current_spends = {}
    tracker = get_redis_usage_tracker()
    if tracker:
        for p in cloud_providers:
            try:
                current_spends[p] = await tracker.get_provider_spend(p)
            except Exception:
                current_spends[p] = _provider_spend_usd.get(p, 0.0)
    else:
        for p in cloud_providers:
            current_spends[p] = _provider_spend_usd.get(p, 0.0)

    total_spend = sum(current_spends.values())

    if total_budget <= 0.0:
        return False  # No budget = no guardrail

    threshold = getattr(settings, "BUDGET_THRESHOLD_PERCENT", 0.90)
    exceeded = total_spend >= (threshold * total_budget)

    if exceeded:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning("log_warning", message=f"Budget threshold exceeded! Spend: ${total_spend:.2f} >= "
            f"{threshold * 100:.0f}% of ${total_budget:.2f}"
        )

    return exceeded


def _get_model_pricing(provider: str, model_name: str) -> ProviderPricing:
    try:
        if provider == "openai":
            mp = settings.OPENAI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(
                    mp.get("input_per_1k_usd", settings.OPENAI_COST_PER_1K_INPUT_USD),
                    mp.get("output_per_1k_usd", settings.OPENAI_COST_PER_1K_OUTPUT_USD),
                )
            return ProviderPricing(
                settings.OPENAI_COST_PER_1K_INPUT_USD, settings.OPENAI_COST_PER_1K_OUTPUT_USD
            )
        if provider == "google_gemini":
            mp = settings.GEMINI_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(
                    mp.get("input_per_1k_usd", settings.GEMINI_COST_PER_1K_INPUT_USD),
                    mp.get("output_per_1k_usd", settings.GEMINI_COST_PER_1K_OUTPUT_USD),
                )
            return ProviderPricing(
                settings.GEMINI_COST_PER_1K_INPUT_USD, settings.GEMINI_COST_PER_1K_OUTPUT_USD
            )
        if provider == "deepseek":
            mp = settings.DEEPSEEK_MODEL_PRICING.get(model_name)
            if mp:
                return ProviderPricing(
                    mp.get("input_per_1k_usd", settings.DEEPSEEK_COST_PER_1K_INPUT_USD),
                    mp.get("output_per_1k_usd", settings.DEEPSEEK_COST_PER_1K_OUTPUT_USD),
                    mp.get("cache_read_per_1k_usd", settings.DEEPSEEK_COST_PER_1K_CACHE_READ_USD),
                )
            return ProviderPricing(
                settings.DEEPSEEK_COST_PER_1K_INPUT_USD,
                settings.DEEPSEEK_COST_PER_1K_OUTPUT_USD,
                settings.DEEPSEEK_COST_PER_1K_CACHE_READ_USD,
            )
        if provider == "xai":
            mp = getattr(settings, "XAI_MODEL_PRICING", {}).get(model_name)
            if mp:
                return ProviderPricing(
                    mp.get("input_per_1k_usd", settings.XAI_COST_PER_1K_INPUT_USD),
                    mp.get("output_per_1k_usd", settings.XAI_COST_PER_1K_OUTPUT_USD),
                )
            return ProviderPricing(
                settings.XAI_COST_PER_1K_INPUT_USD, settings.XAI_COST_PER_1K_OUTPUT_USD
            )
        # ollama
        return ProviderPricing(
            settings.OLLAMA_COST_PER_1K_INPUT_USD, settings.OLLAMA_COST_PER_1K_OUTPUT_USD
        )
    except Exception:
        return ProviderPricing(0.0, 0.0)


async def _tenant_budget_remaining(kind: str, id_: str | None) -> float:
    if not id_:
        return float("inf")
    today = _today_str()
    if kind == "user":
        budget = _tenant_user_daily_budget_usd
        entry = _tenant_user_spend_usd.get(id_)
        tracker = None
        try:
            tracker = get_redis_usage_tracker()
        except Exception:
            tracker = None
        if tracker is not None:
            try:
                spent = await tracker.get_tenant_spend("user", id_, today)
                entry = {"date": today, "usd": spent}
                _tenant_user_spend_usd[id_] = entry
            except Exception:
                if not entry or entry.get("date") != today:
                    _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
                    entry = _tenant_user_spend_usd[id_]
        elif not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_user_spend_usd[id_]
        return (
            max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0))
            if budget > 0
            else float("inf")
        )
    else:  # project
        budget = _tenant_project_daily_budget_usd
        entry = _tenant_project_spend_usd.get(id_)
        tracker = None
        try:
            tracker = get_redis_usage_tracker()
        except Exception:
            tracker = None
        if tracker is not None:
            try:
                spent = await tracker.get_tenant_spend("project", id_, today)
                entry = {"date": today, "usd": spent}
                _tenant_project_spend_usd[id_] = entry
            except Exception:
                if not entry or entry.get("date") != today:
                    _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
                    entry = _tenant_project_spend_usd[id_]
        elif not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
            entry = _tenant_project_spend_usd[id_]
        return (
            max(0.0, (budget or 0.0) - (entry.get("usd", 0.0) or 0.0))
            if budget > 0
            else float("inf")
        )


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Thread sem loop: usa o loop onde o Redis foi inicializado, quando disponível.
        try:
            from app.core.infrastructure.redis_manager import get_redis_manager

            bridge_loop = get_redis_manager().event_loop
        except Exception:
            bridge_loop = None

        if bridge_loop and bridge_loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, bridge_loop).result()
        return asyncio.run(coro)
    loop.create_task(coro)
    return None


def _register_tenant_spend(kind: str, id_: str | None, cost_usd: float):
    if not id_:
        return
    today = _today_str()
    cost_usd = max(0.0, float(cost_usd))
    tracker = None
    try:
        tracker = get_redis_usage_tracker()
    except Exception:
        tracker = None
    if kind == "user":
        entry = _tenant_user_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_user_spend_usd[id_] = {"date": today, "usd": 0.0}
        if tracker is not None:
            try:
                total = _run_async(tracker.increment_tenant_spend("user", id_, cost_usd, today))
                if total is not None:
                    _tenant_user_spend_usd[id_]["usd"] = total
                else:
                    _tenant_user_spend_usd[id_]["usd"] = (
                        _tenant_user_spend_usd[id_]["usd"] or 0.0
                    ) + cost_usd
            except Exception:
                _tenant_user_spend_usd[id_]["usd"] = (
                    _tenant_user_spend_usd[id_]["usd"] or 0.0
                ) + cost_usd
        else:
            _tenant_user_spend_usd[id_]["usd"] = (
                _tenant_user_spend_usd[id_]["usd"] or 0.0
            ) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="user", id=id_).inc(cost_usd)
        except Exception:
            pass
    else:
        entry = _tenant_project_spend_usd.get(id_)
        if not entry or entry.get("date") != today:
            _tenant_project_spend_usd[id_] = {"date": today, "usd": 0.0}
        if tracker is not None:
            try:
                total = _run_async(
                    tracker.increment_tenant_spend("project", id_, cost_usd, today)
                )
                if total is not None:
                    _tenant_project_spend_usd[id_]["usd"] = total
                else:
                    _tenant_project_spend_usd[id_]["usd"] = (
                        _tenant_project_spend_usd[id_]["usd"] or 0.0
                    ) + cost_usd
            except Exception:
                _tenant_project_spend_usd[id_]["usd"] = (
                    _tenant_project_spend_usd[id_]["usd"] or 0.0
                ) + cost_usd
        else:
            _tenant_project_spend_usd[id_]["usd"] = (
                _tenant_project_spend_usd[id_]["usd"] or 0.0
            ) + cost_usd
        try:
            LLM_TENANT_SPEND_USD.labels(kind="project", id=id_).inc(cost_usd)
        except Exception:
            pass


def register_usage(
    provider: str, user_id: str | None, project_id: str | None, cost_usd: float
):
    cost = max(0.0, float(cost_usd))
    if cost == 0.0:
        return
    tracker = None
    try:
        tracker = get_redis_usage_tracker()
    except Exception:
        tracker = None
    total_spend = _provider_spend_usd.get(provider, 0.0)
    if tracker is not None:
        try:
            total_spend = _run_async(tracker.increment_provider_spend(provider, cost))
            if total_spend is None:
                total_spend = (_provider_spend_usd.get(provider, 0.0) or 0.0) + cost
        except Exception:
            total_spend = (_provider_spend_usd.get(provider, 0.0) or 0.0) + cost
    else:
        total_spend = (_provider_spend_usd.get(provider, 0.0) or 0.0) + cost
    _provider_spend_usd[provider] = total_spend
    try:
        LLM_PROVIDER_SPEND_USD.labels(provider=provider, category="total").inc(cost)
        budget = _provider_budgets_usd.get(provider, 0.0)
        remaining = max(0.0, budget - total_spend)
        LLM_PROVIDER_BUDGET_REMAINING.labels(provider=provider).set(remaining)
    except Exception:
        pass
    if user_id:
        _register_tenant_spend("user", user_id, cost)
    if project_id:
        _register_tenant_spend("project", project_id, cost)
