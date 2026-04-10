from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.llm import ModelPriority, ModelRole
from app.services.llm_service import LLMService, LLMServiceError, get_llm_service

router = APIRouter(tags=["LLM"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class LLMInvokeRequest(BaseModel):
    prompt: str = Field(..., description="Prompt enviado ao LLM")
    role: str = Field(..., description="Papel do modelo (e.g., orchestrator, code_generator)")
    priority: str = Field(
        ...,
        description="Prioridade de custo/latência (e.g., local_only, fast_and_cheap, high_quality)",
    )
    timeout_seconds: int | None = Field(None, ge=0, description="Timeout máximo para a invocação")
    task_type: str | None = Field(None, description="Tipo de tarefa para roteamento por politica")
    complexity: str | None = Field(None, description="Complexidade da tarefa (low/medium/high)")
    policy_overrides: dict[str, Any] | None = Field(
        None, description="Overrides de politica/LLM para esta chamada"
    )
    project_id: str | None = Field(None, description="Identificador do projeto (orçamentação)")


class LLMInvokeResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str
    input_tokens: int | None = Field(
        None, description="Total de tokens de entrada reais, quando disponível"
    )
    output_tokens: int | None = Field(
        None, description="Total de tokens de saída reais, quando disponível"
    )
    cost_usd: float | None = Field(None, description="Custo em USD baseado em pricing do provedor")


class LLMCacheStatusResponse(BaseModel):
    total_cached: int
    cache_entries: list[dict[str, Any]]


class CircuitBreakerStatus(BaseModel):
    provider: str
    state: str
    failure_count: int
    last_failure_time: float | None


class InvalidateResponseCacheRequest(BaseModel):
    prompt: str | None = None
    role: str | None = None
    priority: str | None = None


# --- Endpoints ---


@router.post(
    "/invoke",
    response_model=LLMInvokeResponse,
    summary="Invoca um LLM com base no papel e prioridade",
)
async def invoke_llm(request: LLMInvokeRequest, service: LLMService = Depends(get_llm_service)):
    """Delega a invocação de um LLM para o LLMService."""
    # ValueError, LLMTimeoutError, e LLMInvocationError são tratados pelo exception handler central.
    role = ModelRole(request.role)
    priority = ModelPriority(request.priority)

    result = await service.invoke_llm(
        prompt=request.prompt,
        role=role,
        priority=priority,
        timeout_seconds=request.timeout_seconds,
        task_type=request.task_type,
        complexity=request.complexity,
        policy_overrides=request.policy_overrides,
        user_id=request.user_id,
        project_id=request.project_id,
    )
    return LLMInvokeResponse(**result)


@router.get(
    "/cache/status",
    response_model=LLMCacheStatusResponse,
    summary="Retorna o status do cache de LLMs",
)
async def get_cache_status(service: LLMService = Depends(get_llm_service)):
    """Delega a busca do status do cache para o LLMService."""
    entries = service.get_cache_status()
    return LLMCacheStatusResponse(total_cached=len(entries), cache_entries=entries)


@router.post("/cache/invalidate", summary="Invalida o cache de LLMs")
async def invalidate_llm_cache(
    provider: str | None = None, service: LLMService = Depends(get_llm_service)
):
    """Delega a invalidação do cache para o LLMService."""
    remaining_count = service.invalidate_cache(provider)
    message = (
        f"Cache invalidado para provider: {provider}"
        if provider
        else "Cache completamente invalidado"
    )
    return {"message": message, "provider": provider, "remaining_cached": remaining_count}


# --- Response Cache Endpoints ---


@router.get(
    "/response-cache/status",
    response_model=LLMCacheStatusResponse,
    summary="Status do cache de respostas (prompts/respostas)",
)
async def get_response_cache_status(service: LLMService = Depends(get_llm_service)):
    """Retorna apenas entradas do cache de respostas."""
    entries = service.get_response_cache_status()
    return LLMCacheStatusResponse(total_cached=len(entries), cache_entries=entries)


@router.post(
    "/response-cache/invalidate", summary="Invalida cache de respostas por prompt/role/priority"
)
async def invalidate_response_cache(
    request: InvalidateResponseCacheRequest, service: LLMService = Depends(get_llm_service)
):
    """Invalida entradas do cache de respostas conforme filtros fornecidos."""
    remaining_count = service.invalidate_response_cache(
        prompt=request.prompt, role=request.role, priority=request.priority
    )
    msg_detail = []
    if request.prompt:
        msg_detail.append("prompt")
    if request.role:
        msg_detail.append("role")
    if request.priority:
        msg_detail.append("priority")
    scope = ",".join(msg_detail) if msg_detail else "all"
    return {"message": f"Response cache invalidated ({scope})", "remaining_cached": remaining_count}


@router.get(
    "/circuit-breakers",
    response_model=list[CircuitBreakerStatus],
    summary="Retorna o status dos circuit breakers",
)
async def get_circuit_breaker_status(service: LLMService = Depends(get_llm_service)):
    """Delega a busca do status dos circuit breakers para o LLMService."""
    return service.get_circuit_breaker_statuses()


@router.post(
    "/circuit-breakers/{provider}/reset", summary="Reseta o circuit breaker de um provedor"
)
async def reset_circuit_breaker(provider: str, service: LLMService = Depends(get_llm_service)):
    """Delega o reset do circuit breaker para o LLMService."""
    try:
        new_state = service.reset_circuit_breaker(provider)
    except LLMServiceError as e:
        detail = str(e)
        status_code = 404 if "não encontrado" in detail.lower() or "not found" in detail.lower() else 500
        raise HTTPException(status_code=status_code, detail=detail) from e
    return {"message": f"Circuit breaker resetado para: {provider}", "new_state": new_state}


@router.get("/providers", summary="Lista provedores configurados de LLMs")
async def list_llm_providers(service: LLMService = Depends(get_llm_service)):
    """Retorna os provedores configurados com seus modelos e estado de habilitação."""
    return service.get_providers()


@router.get("/health", summary="Health check do sistema de LLMs")
async def llm_health(service: LLMService = Depends(get_llm_service)):
    """Delega a verificação de saúde para o LLMService."""
    return await service.get_health_status()


class ABExperimentSetRequest(BaseModel):
    experiment_id: int


@router.post("/ab/set-experiment", summary="Define experimento A/B para seleção de LLM por usuário")
async def set_ab_experiment(req: ABExperimentSetRequest):
    settings.LLM_AB_EXPERIMENT_ID = int(req.experiment_id)
    return {"status": "ok", "LLM_AB_EXPERIMENT_ID": int(req.experiment_id)}


# --- Budget & Pricing Endpoints ---

@router.get("/budget/summary", summary="Retorna resumo de budget e gastos por provedor")
async def get_budget_summary():
    """
    Retorna resumo de budget e gastos por provedor.
    
    Utilizado pelo Budget Panel do frontend para mostrar consumo em tempo real.
    """
    from app.core.llm import pricing
    from datetime import datetime
    
    providers = ["openai", "google_gemini", "deepseek", "ollama"]
    
    provider_data = []
    total_spent = 0.0
    total_budget = 0.0
    
    for provider in providers:
        spent = pricing._provider_spend_usd.get(provider, 0.0)
        budget = pricing._provider_budgets_usd.get(provider, 0.0)
        remaining = max(0.0, budget - spent)
        percentage = (spent / budget * 100) if budget > 0 else 0.0
        
        provider_data.append({
            "provider": provider,
            "spent": spent,
            "budget": budget,
            "remaining": remaining,
            "percentage": percentage
        })
        
        total_spent += spent
        total_budget += budget
    
    guardrail_active = total_spent >= (total_budget * 0.9)
    
    return {
        "providers": provider_data,
        "total_spent": total_spent,
        "total_budget": total_budget,
        "guardrail_active": guardrail_active,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/pricing/providers", summary="Retorna tabela de preços por provedor")
async def get_provider_pricing():
    """Retorna tabela de preços por provedor (USD por 1K tokens)."""
    from app.core.llm import pricing
    
    return {
        provider: {
            "input_per_1k_usd": p.input_per_1k_usd,
            "output_per_1k_usd": p.output_per_1k_usd,
            "cache_read_per_1k_usd": getattr(p, "cache_read_per_1k_usd", None)
        }
        for provider, p in pricing._provider_pricing.items()
    }
