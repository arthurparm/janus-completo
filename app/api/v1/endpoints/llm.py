"""
API endpoints para gerenciamento e monitoramento do LLM Manager (Sprint 10).
"""
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_manager import (
    get_llm_client,
    ModelRole,
    ModelPriority,
    invalidate_cache,
    _llm_cache,
    _provider_circuit_breakers,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Schemas ---

class LLMInvokeRequest(BaseModel):
    """Request para invocar um LLM."""
    prompt: str = Field(..., description="Prompt a ser enviado ao LLM")
    role: str = Field(default="orchestrator",
                      description="Papel do modelo: orchestrator, code_generator, knowledge_curator")
    priority: str = Field(default="local_only", description="Prioridade: local_only, fast_and_cheap, high_quality")
    timeout_seconds: Optional[int] = Field(default=None, description="Timeout customizado em segundos")


class LLMInvokeResponse(BaseModel):
    """Response da invocação do LLM."""
    response: str = Field(..., description="Resposta gerada pelo LLM")
    provider: str = Field(..., description="Provedor utilizado")
    model: str = Field(..., description="Modelo utilizado")
    role: str = Field(..., description="Papel do modelo")


class LLMCacheStatusResponse(BaseModel):
    """Status do cache de LLMs."""
    total_cached: int = Field(..., description="Total de LLMs em cache")
    cache_entries: list[Dict[str, Any]] = Field(..., description="Entradas do cache")


class CircuitBreakerStatus(BaseModel):
    """Status de um circuit breaker."""
    provider: str
    state: str
    failure_count: int
    last_failure_time: Optional[float]


class LLMHealthResponse(BaseModel):
    """Health check do sistema de LLMs."""
    status: str
    total_providers: int
    circuit_breakers: list[CircuitBreakerStatus]
    cache_status: Dict[str, int]


# --- Endpoints ---

@router.post("/invoke", response_model=LLMInvokeResponse)
async def invoke_llm(request: LLMInvokeRequest):
    """
    Invoca um LLM com base no papel e prioridade especificados.

    O sistema automaticamente seleciona o melhor provedor disponível
    e implementa fallback para Ollama caso APIs de nuvem falhem.
    """
    try:
        # Converter strings para enums
        try:
            role = ModelRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Papel inválido: {request.role}. Opções: orchestrator, code_generator, knowledge_curator"
            )

        try:
            priority = ModelPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Prioridade inválida: {request.priority}. Opções: local_only, fast_and_cheap, high_quality"
            )

        # Obter cliente LLM
        client = get_llm_client(role=role, priority=priority)

        # Invocar com timeout customizado se fornecido
        response = client.send(request.prompt, timeout_s=request.timeout_seconds)

        return LLMInvokeResponse(
            response=response,
            provider=client.provider,
            model=client.model,
            role=client.role.value
        )

    except ValueError as e:
        logger.warning(f"Erro de validação ao invocar LLM: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        logger.error(f"Timeout ao invocar LLM: {e}")
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao invocar LLM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao invocar LLM: {str(e)}")


@router.get("/cache/status", response_model=LLMCacheStatusResponse)
async def get_cache_status():
    """
    Retorna o status do cache de LLMs.

    Mostra todos os LLMs em cache, com informações sobre idade,
    provedor e número de falhas consecutivas.
    """
    try:
        entries = []
        for key, cached in _llm_cache.items():
            age_seconds = (cached.created_at.timestamp())
            entries.append({
                "cache_key": key,
                "provider": cached.provider,
                "consecutive_failures": cached.consecutive_failures,
                "created_at": cached.created_at.isoformat(),
            })

        return LLMCacheStatusResponse(
            total_cached=len(_llm_cache),
            cache_entries=entries
        )
    except Exception as e:
        logger.error(f"Erro ao obter status do cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate")
async def invalidate_llm_cache(provider: Optional[str] = None):
    """
    Invalida o cache de LLMs.

    Se 'provider' for especificado, invalida apenas o cache desse provedor.
    Caso contrário, invalida todo o cache.
    """
    try:
        invalidate_cache(provider=provider)

        message = f"Cache invalidado para provider: {provider}" if provider else "Cache completamente invalidado"

        return {
            "message": message,
            "provider": provider,
            "remaining_cached": len(_llm_cache)
        }
    except Exception as e:
        logger.error(f"Erro ao invalidar cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers", response_model=list[CircuitBreakerStatus])
async def get_circuit_breaker_status():
    """
    Retorna o status de todos os circuit breakers dos provedores.

    Circuit breakers isolam falhas de provedores específicos,
    evitando cascata de erros e permitindo recuperação gradual.
    """
    try:
        statuses = []
        for provider, cb in _provider_circuit_breakers.items():
            statuses.append(CircuitBreakerStatus(
                provider=provider,
                state=cb.state.value,
                failure_count=cb.failure_count,
                last_failure_time=cb.last_failure_time
            ))

        return statuses
    except Exception as e:
        logger.error(f"Erro ao obter status dos circuit breakers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breakers/{provider}/reset")
async def reset_circuit_breaker(provider: str):
    """
    Reseta o circuit breaker de um provedor específico.

    Útil para forçar a recuperação manual após correção de problemas.
    """
    try:
        if provider not in _provider_circuit_breakers:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker não encontrado para provider: {provider}"
            )

        cb = _provider_circuit_breakers[provider]
        cb.reset()

        return {
            "message": f"Circuit breaker resetado para provider: {provider}",
            "provider": provider,
            "new_state": cb.state.value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao resetar circuit breaker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=LLMHealthResponse)
async def health_check():
    """
    Health check completo do sistema de gerenciamento de LLMs.

    Verifica:
    - Estado dos circuit breakers
    - Status do cache
    - Disponibilidade geral do sistema
    """
    try:
        # Status dos circuit breakers
        cb_statuses = []
        open_circuits = 0

        for provider, cb in _provider_circuit_breakers.items():
            cb_statuses.append(CircuitBreakerStatus(
                provider=provider,
                state=cb.state.value,
                failure_count=cb.failure_count,
                last_failure_time=cb.last_failure_time
            ))
            if cb.state.value == "OPEN":
                open_circuits += 1

        # Status do cache
        cache_status = {
            "total_cached": len(_llm_cache),
            "providers_in_cache": len(set(c.provider for c in _llm_cache.values()))
        }

        # Determinar status geral
        if open_circuits >= len(_provider_circuit_breakers) - 1:  # Todos exceto "unknown"
            status = "degraded"
        elif open_circuits > 0:
            status = "partial"
        else:
            status = "healthy"

        return LLMHealthResponse(
            status=status,
            total_providers=len(_provider_circuit_breakers),
            circuit_breakers=cb_statuses,
            cache_status=cache_status
        )
    except Exception as e:
        logger.error(f"Erro no health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """
    Lista todos os provedores de LLM configurados.

    Retorna informações sobre disponibilidade e configuração de cada provedor.
    """
    try:
        from app.config import settings

        providers = [
            {
                "name": "Ollama (Local)",
                "provider_key": "ollama",
                "base_url": settings.OLLAMA_HOST,
                "models": {
                    "orchestrator": settings.OLLAMA_ORCHESTRATOR_MODEL,
                    "code_generator": settings.OLLAMA_CODER_MODEL,
                    "knowledge_curator": settings.OLLAMA_CURATOR_MODEL,
                },
                "always_available": True,
            },
            {
                "name": "Google Gemini",
                "provider_key": "google_gemini",
                "model": settings.GEMINI_MODEL_NAME,
                "api_key_configured": bool(getattr(settings.GEMINI_API_KEY, 'get_secret_value', lambda: None)()),
            },
            {
                "name": "OpenAI",
                "provider_key": "openai",
                "model": settings.OPENAI_MODEL_NAME,
                "api_key_configured": bool(getattr(settings.OPENAI_API_KEY, 'get_secret_value', lambda: None)()),
            }
        ]

        return {"providers": providers}
    except Exception as e:
        logger.error(f"Erro ao listar provedores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
