import structlog
from typing import List, Dict, Any

from app.repositories.memory_repository import memory_repository
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    pass


class MemoryService:
    """
    Camada de serviço para operações relacionadas à memória episódica.
    Orquestra a lógica de negócio, delegando o acesso a dados para o repositório.
    """

    async def add_experience(self, type: str, content: str, metadata: Dict[str, Any]) -> Experience:
        """
        Cria uma nova experiência e a delega para o repositório salvar.
        """
        logger.info("Criando e salvando nova experiência via serviço", type=type)
        try:
            experience = Experience(
                type=type,
                content=content,
                metadata=metadata
            )
            await memory_repository.save_experience(experience)
            return experience
        except Exception as e:
            logger.error("Erro no serviço de memória ao adicionar experiência", exc_info=e)
            raise MemoryServiceError("Falha ao adicionar experiência.") from e

    async def recall_experiences(self, query: str) -> List[Dict[str, Any]]:
        """
        Delega a busca por experiências para o repositório.
        """
        logger.info("Buscando experiências via serviço", query=query)
        try:
            return await memory_repository.search_experiences(query=query)
        except Exception as e:
            logger.error("Erro no serviço de memória ao buscar experiências", exc_info=e)
            raise MemoryServiceError("Falha ao buscar experiências.") from e


# Instância única do serviço
memory_service = MemoryService()
