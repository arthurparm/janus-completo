import structlog
from typing import Dict, Any, Optional
from fastapi import Depends

from app.core.infrastructure.message_broker import MessageBroker, get_broker

logger = structlog.get_logger(__name__)

class TaskRepositoryError(Exception):
    """Base exception for task repository errors."""
    pass

class TaskRepository:
    """
    Camada de Repositório para tarefas assíncronas (Message Broker).
    Recebe sua dependência de infraestrutura via DI.
    """

    def __init__(self, broker: MessageBroker):
        self._broker = broker

    async def publish_message(self, queue_name: str, message: str):
        """Publica uma mensagem em uma fila específica."""
        logger.debug("Publicando mensagem no repositório de tarefas", queue=queue_name)
        try:
            await self._broker.publish(queue_name=queue_name, message=message)
        except Exception as e:
            logger.error("Erro no repositório ao publicar mensagem", exc_info=e)
            raise TaskRepositoryError("Falha ao publicar mensagem no broker.") from e

    async def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Busca informações de uma fila específica."""
        logger.debug("Buscando informações da fila no repositório", queue=queue_name)
        try:
            return await self._broker.get_queue_info(queue_name)
        except Exception as e:
            logger.error("Erro no repositório ao buscar informações da fila", exc_info=e)
            raise TaskRepositoryError(f"Falha ao buscar informações da fila '{queue_name}'.") from e

    async def is_broker_healthy(self) -> bool:
        """Verifica a saúde do message broker."""
        try:
            return await self._broker.health_check()
        except Exception:
            return False

    async def get_queue_policy(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Consulta a política/argumentos atuais de uma fila via Management API."""
        logger.debug("Buscando política da fila no repositório", queue=queue_name)
        try:
            return await self._broker.get_queue_policy(queue_name)
        except Exception as e:
            logger.error("Erro no repositório ao buscar política da fila", exc_info=e)
            raise TaskRepositoryError(f"Falha ao buscar política da fila '{queue_name}'.") from e

    async def validate_queue_policy(self, queue_name: str) -> Dict[str, Any]:
        """Valida argumentos da fila contra a configuração esperada."""
        logger.debug("Validando política da fila no repositório", queue=queue_name)
        try:
            return await self._broker.validate_queue_policy(queue_name)
        except Exception as e:
            logger.error("Erro no repositório ao validar política da fila", exc_info=e)
            raise TaskRepositoryError(f"Falha ao validar política da fila '{queue_name}'.") from e

    async def reconcile_queue_policy(self, queue_name: str, force_delete: bool = True) -> Dict[str, Any]:
        """Reconciliar política (deletando e recriando fila se divergente)."""
        logger.debug("Reconciliação de política da fila no repositório", queue=queue_name)
        try:
            return await self._broker.reconcile_queue_policy(queue_name, force_delete=force_delete)
        except Exception as e:
            logger.error("Erro no repositório ao reconciliar política da fila", exc_info=e)
            raise TaskRepositoryError(f"Falha ao reconciliar política da fila '{queue_name}'.") from e


# Padrão de Injeção de Dependência: Getter para o repositório
def get_task_repository(broker: MessageBroker = Depends(get_broker)) -> TaskRepository:
    return TaskRepository(broker)
