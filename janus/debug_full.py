from app.config import settings
from app.core.llm.factory import _validate_deepseek_key, _validate_gemini_key, _validate_openai_key
from app.core.llm.pricing import _budget_allows, _get_model_pricing
from app.core.llm.rate_limiter import get_rate_limiter
from app.core.llm.resilience import _circuit_closed

# Simula exatamente como cloud_catalog é construído
cloud_catalog = [
    {
        "name": "DeepSeek",
        "provider_key": "deepseek",
        "enabled": _validate_deepseek_key(
            getattr(settings.DEEPSEEK_API_KEY, "get_secret_value", lambda: None)()
        ),
        "models": (
            settings.DEEPSEEK_MODELS
            if getattr(settings, "DEEPSEEK_MODELS", None)
            else [settings.DEEPSEEK_MODEL_NAME]
        ),
    },
    {
        "name": "Google Gemini",
        "provider_key": "google_gemini",
        "enabled": _validate_gemini_key(
            getattr(settings.GEMINI_API_KEY, "get_secret_value", lambda: None)()
        ),
        "models": (
            settings.GEMINI_MODELS
            if getattr(settings, "GEMINI_MODELS", None)
            else [settings.GEMINI_MODEL_NAME]
        ),
    },
    {
        "name": "OpenAI",
        "provider_key": "openai",
        "enabled": _validate_openai_key(
            getattr(settings.OPENAI_API_KEY, "get_secret_value", lambda: None)()
        ),
        "models": (
            settings.OPENAI_MODELS
            if getattr(settings, "OPENAI_MODELS", None)
            else [settings.OPENAI_MODEL_NAME]
        ),
    },
]

raw_role_candidates = getattr(settings, "LLM_CLOUD_MODEL_CANDIDATES", {}).get("orchestrator", [])
role_candidates_map = {}
for spec in raw_role_candidates:
    try:
        provider_key, model_name = spec.split(":", 1)
        role_candidates_map.setdefault(provider_key.strip(), set()).add(model_name.strip())
    except Exception:
        pass

print("=== Cloud Catalog Iteration ===")
rate_limiter = get_rate_limiter()
candidates = []

for p in cloud_catalog:
    provider_key = p["provider_key"]
    print(f"\nProvider: {p['name']} ({provider_key})")
    print(f"  enabled: {p['enabled']}")
    print(f"  circuit_closed: {_circuit_closed(provider_key)}")
    print(f"  budget_allows: {_budget_allows(provider_key)}")

    if not (p["enabled"] and _circuit_closed(provider_key) and _budget_allows(provider_key)):
        print("  SKIPPED - failed checks")
        continue

    model_list = list(role_candidates_map.get(provider_key, set())) or p["models"]
    print(f"  model_list: {model_list}")

    for model_name in model_list:
        is_avail = rate_limiter.is_available(provider_key, model_name)
        print(f"    Model {model_name}: rate_limit_available={is_avail}")

        if not is_avail:
            continue

        pricing = _get_model_pricing(provider_key, model_name)
        cost = pricing.input_per_1k_usd + pricing.output_per_1k_usd
        print(f"      cost_per_1k: {cost}")

        candidates.append(
            {
                "name": p["name"],
                "provider_key": provider_key,
                "model_name": model_name,
                "cost_per_1k": cost,
            }
        )

print(f"\n=== Final Candidates ({len(candidates)}) ===")
for c in candidates:
    print(f"  {c['provider_key']}:{c['model_name']} (cost={c['cost_per_1k']:.4f})")
