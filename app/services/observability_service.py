import structlog
from typing import Dict, Any, List, Optional
from fastapi import Depends, Request

from app.repositories.observability_repository import ObservabilityRepository, get_observability_repository, \
    ObservabilityRepositoryError
from app.core.monitoring.poison_pill_handler import QuarantinedMessage

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---

class ObservabilityServiceError(Exception):
    """Base exception for observability service errors."""
    pass

class MessageNotFoundError(ObservabilityServiceError):
    """Raised when a message is not found in quarantine."""
    pass

# --- Observability Service ---

class ObservabilityService:
    """
    Camada de serviço para observabilidade, saúde do sistema e resiliência.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def __init__(self, repo: ObservabilityRepository):
        self._repo = repo

    async def get_system_health(self) -> Dict[str, Any]:
        logger.info("Buscando saúde agregada do sistema via serviço.")
        try:
            return await self._repo.get_system_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> Dict[str, Dict[str, Any]]:
        logger.info("Disparando health check de todos os componentes via serviço.")
        try:
            return await self._repo.check_all_components()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao executar health checks", exc_info=e)
            raise ObservabilityServiceError("Falha ao executar os health checks.") from e

    def get_quarantined_messages(self, queue: Optional[str] = None) -> List[QuarantinedMessage]:
        logger.info("Buscando mensagens em quarentena via serviço", queue=queue)
        return self._repo.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.info("Liberando mensagem da quarentena via serviço", message_id=message_id)
        try:
            msg = self._repo.release_from_quarantine(message_id, allow_retry)
            if not msg:
                raise MessageNotFoundError(f"Mensagem com ID '{message_id}' não encontrada na quarentena.")
            return msg
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao liberar mensagem", exc_info=e)
            raise ObservabilityServiceError("Falha ao liberar mensagem da quarentena.") from e

    def get_poison_pill_stats(self, queue: Optional[str] = None) -> Dict[str, Any]:
        logger.info("Buscando estatísticas de poison pills via serviço", queue=queue)
        return self._repo.get_poison_pill_stats(queue=queue)

    def get_metrics_summary(self) -> Dict[str, Any]:
        logger.info("Coletando resumo de métricas do sistema via serviço.")
        try:
            return self._repo.get_metrics_summary()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar resumo de métricas", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar o resumo de métricas.") from e


# Padrão de Injeção de Dependência: Getter para o serviço
def get_observability_service(request: Request) -> ObservabilityService:
    return request.app.state.observability_service
