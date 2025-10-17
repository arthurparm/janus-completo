import structlog
from typing import Dict, Any, List, Optional
from fastapi import Request

from app.repositories.llm_repository import LLMRepository, LLMRepositoryError
from app.core.llm import ModelRole, ModelPriority
from app.core.monitoring.health_monitor import check_llm_manager_health

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
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: LLMRepository):
        self._repo = repo

    def invoke_llm(
            self,
            prompt: str,
            role: ModelRole,
            priority: ModelPriority,
            timeout_seconds: Optional[int],
            user_id: Optional[str] = None,
            project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("Orquestrando invocação de LLM via serviço", role=role.value, priority=priority.value)
        try:
            return self._repo.invoke_llm(prompt, role, priority, timeout_seconds, user_id=user_id,
                                         project_id=project_id)
        except TimeoutError as e:
            logger.error("Timeout no serviço de LLM", exc_info=e)
            raise LLMTimeoutError(str(e)) from e
        except LLMRepositoryError as e:
            logger.error("Erro no repositório de LLM", exc_info=e)
            raise LLMInvocationError(f"Falha ao invocar LLM: {e}") from e

    def get_cache_status(self) -> List[Dict[str, Any]]:
        logger.info("Buscando status do cache de LLMs via serviço.")
        return self._repo.get_cache_entries()

    def invalidate_cache(self, provider: Optional[str] = None) -> int:
        logger.info("Orquestrando invalidação de cache de LLMs via serviço", provider=provider)
        return self._repo.invalidate_cache(provider)

    def get_circuit_breaker_statuses(self) -> List[Dict[str, Any]]:
        logger.info("Buscando status dos circuit breakers via serviço.")
        return self._repo.get_circuit_breakers()

    def reset_circuit_breaker(self, provider: str) -> str:
        logger.info("Orquestrando reset de circuit breaker via serviço", provider=provider)
        try:
            self._repo.reset_circuit_breaker(provider)
            breakers = self._repo.get_circuit_breakers()
            for cb in breakers:
                if cb["provider"] == provider:
                    return cb["state"]
            return "unknown"
        except LLMRepositoryError as e:
            raise LLMServiceError(str(e)) from e

    def get_providers(self) -> List[Dict[str, Any]]:
        logger.info("Listando provedores de LLMs via serviço.")
        return self._repo.list_providers()

    async def get_health_status(self) -> Dict[str, Any]:
        logger.info("Verificando saúde do sistema de LLMs via serviço.")
        # Usa health monitor central para consolidar o estado dos circuit breakers e cache
        return await check_llm_manager_health()

# Padrão de Injeção de Dependência: Getter para o serviço
def get_llm_service(request: Request) -> LLMService:
    return request.app.state.llm_service
