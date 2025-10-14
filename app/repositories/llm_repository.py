import structlog
from typing import Dict, Any, List, Optional

from app.core.llm import (
    get_llm_client,
    ModelRole,
    ModelPriority,
    invalidate_cache,
    _llm_cache,
    _provider_circuit_breakers
)

logger = structlog.get_logger(__name__)

class LLMRepositoryError(Exception):
    """Base exception for LLM repository errors."""
    pass

class LLMRepository:
    """
    Camada de Repositório para o Cérebro Híbrido (LLMs).
    Abstrai todas as interações diretas com a infraestrutura de LLMs.
    """

    def invoke_llm(self, prompt: str, role: ModelRole, priority: ModelPriority, timeout_seconds: Optional[int]) -> Dict[
        str, Any]:
        logger.debug("Invocando LLM via repositório", role=role.value, priority=priority.value)
        try:
            client = get_llm_client(role=role, priority=priority)
            response = client.send(prompt, timeout_s=timeout_seconds)
            return {
                "response": response,
                "provider": client.provider,
                "model": client.model,
                "role": client.role.value
            }
        except Exception as e:
            logger.error("Erro no repositório ao invocar LLM", exc_info=e)
            raise LLMRepositoryError(f"Falha ao invocar LLM: {e}") from e

    def get_cache_entries(self) -> List[Dict[str, Any]]:
        logger.debug("Buscando entradas do cache de LLMs no repositório.")
        entries = []
        for key, cached in _llm_cache.items():
            entries.append({
                "cache_key": key,
                "provider": cached.provider,
                "consecutive_failures": cached.consecutive_failures,
                "created_at": cached.created_at.isoformat(),
            })
        return entries

    def invalidate_cache(self, provider: Optional[str] = None) -> int:
        logger.debug("Invalidando cache de LLMs via repositório", provider=provider)
        invalidate_cache(provider=provider)
        return len(_llm_cache)

    def get_circuit_breakers(self) -> List[Dict[str, Any]]:
        logger.debug("Buscando status dos circuit breakers no repositório.")
        statuses = []
        for provider, cb in _provider_circuit_breakers.items():
            statuses.append({
                "provider": provider,
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time
            })
        return statuses

    def reset_circuit_breaker(self, provider: str):
        logger.debug("Resetando circuit breaker via repositório", provider=provider)
        if provider not in _provider_circuit_breakers:
            raise LLMRepositoryError(f"Provedor '{provider}' não encontrado.")
        cb = _provider_circuit_breakers[provider]
        cb.reset()


# Padrão de Injeção de Dependência: Getter para o repositório
def get_llm_repository() -> LLMRepository:
    return LLMRepository()
