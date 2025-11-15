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

    async def get_llm_manager_health(self) -> Dict[str, Any]:
        logger.info("Checando saúde do LLM Manager via serviço.")
        try:
            return await self._repo.get_llm_manager_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar LLM Manager", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do LLM Manager.") from e

    async def get_multi_agent_system_health(self) -> Dict[str, Any]:
        logger.info("Checando saúde do Multi-Agent System via serviço.")
        try:
            return await self._repo.get_multi_agent_system_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar Multi-Agent System", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do sistema multi-agente.") from e

    async def get_poison_pill_handler_health(self) -> Dict[str, Any]:
        logger.info("Checando saúde do Poison Pill Handler via serviço.")
        try:
            return await self._repo.get_poison_pill_handler_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar Poison Pill Handler", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do handler de poison pills.") from e

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

    def cleanup_expired_quarantine(self) -> Dict[str, Any]:
        logger.info("Limpando mensagens expiradas da quarentena via serviço.")
        try:
            removed = self._repo.cleanup_expired_quarantine()
            return {"removed": removed}
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao limpar quarentena expirada", exc_info=e)
            raise ObservabilityServiceError("Falha ao limpar a quarentena expirada.") from e

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

    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        logger.info("Coletando métricas agregadas por usuário", user_id=user_id)
        try:
            return self._repo.get_user_metrics(user_id)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar métricas por usuário", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar métricas por usuário.") from e

    def get_user_activity(self, user_id: str) -> Dict[str, Any]:
        logger.info("Coletando atividade agregada por usuário", user_id=user_id)
        try:
            return self._repo.get_user_activity(user_id)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar atividade por usuário", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar atividade por usuário.") from e

    async def get_graph_audit_report(self) -> Dict[str, Any]:
        logger.info("Executando auditoria de grafo via serviço.")
        try:
            return await self._repo.get_graph_audit_report()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao auditar grafo", exc_info=e)
            raise ObservabilityServiceError("Falha ao auditar o grafo.") from e


# Padrão de Injeção de Dependência: Getter para o serviço
def get_observability_service(request: Request) -> ObservabilityService:
    return request.app.state.observability_service
