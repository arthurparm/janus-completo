import structlog
from typing import Dict, Any, Optional

from app.core.infrastructure.message_broker import message_broker

logger = structlog.get_logger(__name__)


class TaskRepositoryError(Exception):
    """Base exception for task repository errors."""
    pass


class TaskRepository:
    """
    Camada de Repositório para tarefas assíncronas (Message Broker).
    Abstrai todas as interações diretas com a infraestrutura de mensageria.
    """

    async def publish_message(self, queue_name: str, message: str):
        """Publica uma mensagem em uma fila específica."""
        logger.debug("Publicando mensagem no repositório de tarefas", queue=queue_name)
        try:
            await message_broker.publish(queue_name=queue_name, message=message)
        except Exception as e:
            logger.error("Erro no repositório ao publicar mensagem", exc_info=e)
            raise TaskRepositoryError("Falha ao publicar mensagem no broker.") from e

    async def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Busca informações de uma fila específica."""
        logger.debug("Buscando informações da fila no repositório", queue=queue_name)
        try:
            return await message_broker.get_queue_info(queue_name)
        except Exception as e:
            logger.error("Erro no repositório ao buscar informações da fila", exc_info=e)
            raise TaskRepositoryError(f"Falha ao buscar informações da fila '{queue_name}'.") from e

    async def is_broker_healthy(self) -> bool:
        """Verifica a saúde do message broker."""
        try:
            return await message_broker.health_check()
        except Exception:
            return False


# Instância única do repositório
task_repository = TaskRepository()
