import structlog
from typing import Dict, Any, List, Optional

from app.repositories.llm_repository import llm_repository, LLMRepositoryError
from app.core.llm import ModelRole, ModelPriority

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMInvocationError(LLMServiceError):
    """Raised on failure to invoke an LLM."""
    pass


class LLMTimeoutError(LLMServiceError):
    """Raised on LLM invocation timeout."""
    pass


# --- LLM Service ---

class LLMService:
    """
    Camada de serviço para gerenciamento do Cérebro Híbrido (LLMs).
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def invoke_llm(self, prompt: str, role: ModelRole, priority: ModelPriority, timeout_seconds: Optional[int]) -> Dict[
        str, Any]:
        logger.info("Orquestrando invocação de LLM via serviço", role=role.value, priority=priority.value)
        try:
            # A lógica de negócio (neste caso, simples delegação) chama o repositório
            return llm_repository.invoke_llm(prompt, role, priority, timeout_seconds)
        except TimeoutError as e:
            # O repositório pode levantar exceções genéricas que o serviço traduz
            logger.error("Timeout no serviço de LLM", exc_info=e)
            raise LLMTimeoutError(str(e)) from e
        except LLMRepositoryError as e:
            logger.error("Erro no repositório de LLM", exc_info=e)
            raise LLMInvocationError(f"Falha ao invocar LLM: {e}") from e

    def get_cache_status(self) -> List[Dict[str, Any]]:
        logger.info("Buscando status do cache de LLMs via serviço.")
        return llm_repository.get_cache_entries()

    def invalidate_cache(self, provider: Optional[str] = None) -> int:
        logger.info("Orquestrando invalidação de cache de LLMs via serviço", provider=provider)
        return llm_repository.invalidate_cache(provider)

    def get_circuit_breaker_statuses(self) -> List[Dict[str, Any]]:
        logger.info("Buscando status dos circuit breakers via serviço.")
        return llm_repository.get_circuit_breakers()

    def reset_circuit_breaker(self, provider: str) -> str:
        logger.info("Orquestrando reset de circuit breaker via serviço", provider=provider)
        try:
            llm_repository.reset_circuit_breaker(provider)
            # Após o reset, buscamos o novo estado para confirmação
            breakers = llm_repository.get_circuit_breakers()
            for cb in breakers:
                if cb["provider"] == provider:
                    return cb["state"]
            return "unknown"  # Fallback caso não encontre
        except LLMRepositoryError as e:
            raise LLMServiceError(str(e)) from e


# Instância única do serviço
llm_service = LLMService()
