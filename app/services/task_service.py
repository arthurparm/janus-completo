import structlog
from typing import Dict, Any, Optional
import json
import uuid

from app.repositories.task_repository import task_repository, TaskRepositoryError

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class TaskServiceError(Exception):
    """Base exception for task service errors."""
    pass


class BrokerConnectionError(TaskServiceError):
    """Raised when the message broker is not available."""
    pass


# --- Task Service ---

class TaskService:
    """
    Camada de serviço para tarefas assíncronas.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    async def create_consolidation_task(
            self,
            mode: str,
            limit: Optional[int],
            experience_id: Optional[str],
            experience_content: Optional[str],
            metadata: Optional[dict]
    ) -> str:
        """
        Cria a mensagem da tarefa e a delega para o repositório publicar.
        """
        logger.info("Criando tarefa de consolidação via serviço", mode=mode)
        try:
            task_id = str(uuid.uuid4())
            message_body = {
                "task_id": task_id,
                "mode": mode,
                "limit": limit,
                "experience_id": experience_id,
                "experience_content": experience_content,
                "metadata": metadata
            }

            await task_repository.publish_message(
                queue_name="janus.knowledge.consolidation",
                message=json.dumps(message_body)
            )
            return task_id
        except TaskRepositoryError as e:
            logger.error("Erro no repositório ao publicar tarefa de consolidação", exc_info=e)
            raise TaskServiceError("Falha ao publicar tarefa de consolidação.") from e

    async def get_queue_details(self, queue_name: str) -> Dict[str, Any]:
        """Delega a busca de detalhes da fila para o repositório."""
        logger.info("Buscando detalhes da fila via serviço", queue_name=queue_name)
        try:
            info = await task_repository.get_queue_info(queue_name)
            if info is None:
                raise TaskServiceError(f"Fila '{queue_name}' não encontrada.")
            return info
        except TaskRepositoryError as e:
            raise TaskServiceError(f"Falha ao buscar detalhes da fila '{queue_name}'.") from e

    async def check_broker_health(self) -> bool:
        """Delega a verificação de saúde do broker para o repositório."""
        logger.debug("Verificando saúde do broker via serviço.")
        return await task_repository.is_broker_healthy()


# Instância única do serviço
task_service = TaskService()
