import structlog
from typing import Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.llm_service import get_llm_service, LLMService
from app.services.system_status_service import system_status_service
from app.config import settings

# Imports internos para dados do modelo/provedor
from app.core.llm.llm_manager import _get_model_pricing, _model_penalty_factors, _model_stats, _budget_remaining

logger = structlog.get_logger(__name__)
web_router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["identity_name"] = getattr(settings, "AGENT_IDENTITY_NAME", None) or settings.APP_NAME
templates.env.globals["app_env"] = settings.ENVIRONMENT


@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@web_router.get("/overview", response_class=HTMLResponse, include_in_schema=False)
async def web_overview(request: Request, service: LLMService = Depends(get_llm_service)):
    providers = service.get_providers()
    breakers = service.get_circuit_breaker_statuses()
    cache_entries = service.get_cache_status()
    system = system_status_service.get_system_status()
    return templates.TemplateResponse(
        "overview.html",
        {
            "request": request,
            "providers": providers,
            "breakers": breakers,
            "cache_entries": cache_entries,
            "system": system,
        },
    )


@web_router.get("/console", response_class=HTMLResponse, include_in_schema=False)
async def web_console(request: Request):
    return templates.TemplateResponse("console_llm.html", {"request": request})


@web_router.get("/health", response_class=HTMLResponse, include_in_schema=False)
async def web_health(request: Request, service: LLMService = Depends(get_llm_service)):
    status = await service.get_health_status()
    system = system_status_service.get_system_status()
    return templates.TemplateResponse("health.html", {"request": request, "status": status, "system": system})


@web_router.get("/operations", response_class=HTMLResponse, include_in_schema=False)
async def web_operations(request: Request, service: LLMService = Depends(get_llm_service)):
    providers = service.get_providers()
    breakers = service.get_circuit_breaker_statuses()
    cache_entries = service.get_cache_status()
    return templates.TemplateResponse(
        "operations.html",
        {
            "request": request,
            "providers": providers,
            "breakers": breakers,
            "cache_entries": cache_entries,
        },
    )


@web_router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def web_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@web_router.get("/models/{model_name}", response_class=HTMLResponse, include_in_schema=False)
async def web_model_detail(request: Request, model_name: str, service: LLMService = Depends(get_llm_service)):
    """Página de detalhes do modelo: custos, limites, orçamento, penalização e estatísticas."""
    providers = service.get_providers()
    breakers = service.get_circuit_breaker_statuses()

    econ = getattr(settings, "LLM_ECONOMY_POLICY", "balanced")
    cap = int(getattr(settings, "LLM_MAX_GENERATION_TOKENS_CAP", 0) or 0)
    min_tokens = int(getattr(settings, "LLM_MIN_GENERATION_TOKENS", 0) or 0)
    max_prompt_length = int(getattr(settings, "LLM_MAX_PROMPT_LENGTH", 20000))
    reasoning_max = int(getattr(settings, "REASONING_MAX_TOKENS", 0) or 0)
    max_costs = getattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", {})
    expected_k_by_role = getattr(settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {})

    prov_details = []
    for p in providers:
        prov_key = p.get("provider") or p.get("provider_key") or "unknown"
        pricing = _get_model_pricing(prov_key, model_name)
        pf = _model_penalty_factors.get(prov_key, {}).get(model_name, 1.0)
        stats = _model_stats.get(prov_key, {}).get(model_name)
        cb_state = next((b["state"] for b in breakers if b.get("provider") == prov_key), "unknown")
        budget_remaining = _budget_remaining(prov_key)

        # Limites por role, assumindo input=0 tokens para máximo teórico
        per_role_limits = []
        for role_key, usd in max_costs.items():
            try:
                usd_val = float(usd)
                out_tokens = (
                    int((usd_val / max(1e-12, pricing.output_per_1k_usd)) * 1000)
                    if usd_val < float("inf") else 10 ** 9
                )
                if cap and cap > 0:
                    out_tokens = min(out_tokens, cap)
                per_role_limits.append({
                    "role": role_key,
                    "max_out_tokens": out_tokens,
                    "usd_cap": usd_val,
                    "expected_k": float(expected_k_by_role.get(role_key, 2.0)),
                })
            except Exception:
                per_role_limits.append({
                    "role": role_key,
                    "max_out_tokens": 0,
                    "usd_cap": float(usd) if usd not in (None, "inf") else float("inf"),
                    "expected_k": float(expected_k_by_role.get(role_key, 2.0)),
                })

        prov_details.append({
            "provider": prov_key,
            "name": p.get("name", prov_key),
            "enabled": bool(p.get("enabled", True)),
            "breaker": cb_state,
            "budget_remaining_usd": budget_remaining,
            "pricing": {
                "input_per_1k_usd": pricing.input_per_1k_usd,
                "output_per_1k_usd": pricing.output_per_1k_usd,
            },
            "penalty_factor": pf,
            "stats": {
                "total_requests": getattr(stats, "total_requests", 0),
                "success_rate": getattr(stats, "success_rate", 0.0),
                "avg_latency": getattr(stats, "avg_latency", 0.0),
                "success_count": getattr(stats, "success_count", 0),
                "failure_count": getattr(stats, "failure_count", 0),
            },
            "per_role_limits": per_role_limits,
        })

    context = {
        "request": request,
        "model_name": model_name,
        "providers": prov_details,
        "cap_tokens": cap,
        "min_tokens": min_tokens,
        "max_prompt_length": max_prompt_length,
        "reasoning_max_tokens": reasoning_max,
        "economy_policy": econ,
        "expected_k_by_role": expected_k_by_role,
    }
    return templates.TemplateResponse("model.html", context)


@web_router.get("/observability", response_class=HTMLResponse, include_in_schema=False)
async def web_observability(request: Request):
    return templates.TemplateResponse("observability.html", {"request": request})


@web_router.get("/poison-pills", response_class=HTMLResponse, include_in_schema=False)
async def web_poison_pills(request: Request):
    return templates.TemplateResponse("poison_pills.html", {"request": request})


@web_router.get("/queues", response_class=HTMLResponse, include_in_schema=False)
async def web_queues(request: Request):
    return templates.TemplateResponse("queues.html", {"request": request})
