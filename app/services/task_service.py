import structlog
from typing import Dict, Any, Optional
import json
import uuid
from fastapi import Request
from datetime import datetime

from app.repositories.task_repository import TaskRepository, TaskRepositoryError
from app.models.schemas import QueueName, TaskMessage

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
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: TaskRepository):
        self._repo = repo

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
            payload = {
                "mode": mode,
                "limit": limit,
                "experience_id": experience_id,
                "experience_content": experience_content,
                "metadata": metadata
            }
            task_message = TaskMessage(
                task_id=task_id,
                task_type="knowledge_consolidation",
                payload=payload,
                timestamp=datetime.utcnow().timestamp()
            )
            serialized = task_message.model_dump_json()

            await self._repo.publish_message(
                queue_name=QueueName.KNOWLEDGE_CONSOLIDATION,
                message=serialized
            )
            return task_id
        except TaskRepositoryError as e:
            logger.error("Erro no repositório ao publicar tarefa de consolidação", exc_info=e)
            raise TaskServiceError("Falha ao publicar tarefa de consolidação.") from e

    async def get_queue_details(self, queue_name: str) -> Dict[str, Any]:
        """Delega a busca de detalhes da fila para o repositório."""
        logger.info("Buscando detalhes da fila via serviço", queue_name=queue_name)
        try:
            info = await self._repo.get_queue_info(queue_name)
            if info is None:
                raise TaskServiceError(f"Fila '{queue_name}' não encontrada.")
            return info
        except TaskRepositoryError as e:
            raise TaskServiceError(f"Falha ao buscar detalhes da fila '{queue_name}'.") from e

    async def check_broker_health(self) -> bool:
        """Delega a verificação de saúde do broker para o repositório."""
        logger.debug("Verificando saúde do broker via serviço.")
        return await self._repo.is_broker_healthy()

    async def get_queue_policy(self, queue_name: str) -> Dict[str, Any]:
        """Delega ao repositório a consulta da política/argumentos da fila."""
        logger.info("Buscando política da fila via serviço", queue_name=queue_name)
        try:
            policy = await self._repo.get_queue_policy(queue_name)
            if policy is None:
                raise TaskServiceError(f"Fila '{queue_name}' não encontrada ou sem política disponível.")
            return policy
        except TaskRepositoryError as e:
            raise TaskServiceError(f"Falha ao buscar política da fila '{queue_name}'.") from e

    async def validate_queue_policy(self, queue_name: str) -> Dict[str, Any]:
        """Valida argumentos atuais da fila contra configuração esperada."""
        logger.info("Validando política da fila via serviço", queue_name=queue_name)
        try:
            return await self._repo.validate_queue_policy(queue_name)
        except TaskRepositoryError as e:
            raise TaskServiceError(f"Falha ao validar política da fila '{queue_name}'.") from e

    async def reconcile_queue_policy(self, queue_name: str, force_delete: bool = True) -> Dict[str, Any]:
        """Reconcilia política (deleta e recria fila se divergente)."""
        logger.info("Reconciliação de política da fila via serviço", queue_name=queue_name)
        try:
            return await self._repo.reconcile_queue_policy(queue_name, force_delete=force_delete)
        except TaskRepositoryError as e:
            raise TaskServiceError(f"Falha ao reconciliar política da fila '{queue_name}'.") from e

# Padrão de Injeção de Dependência: Getter para o serviço
def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service
