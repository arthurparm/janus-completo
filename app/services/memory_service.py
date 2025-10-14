import structlog
from typing import List, Dict, Any, Optional  # Added Optional
from fastapi import Request

from app.repositories.memory_repository import MemoryRepository
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    pass

class MemoryService:
    """
    Camada de serviço para operações relacionadas à memória episódica.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: MemoryRepository):
        self._repo = repo

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
            await self._repo.save_experience(experience)
            return experience
        except Exception as e:
            logger.error("Erro no serviço de memória ao adicionar experiência", exc_info=e)
            raise MemoryServiceError("Falha ao adicionar experiência.") from e

    async def recall_experiences(self, query: str, limit: Optional[int] = None) -> List[
        Dict[str, Any]]:  # Added limit parameter
        """
        Delega a busca por experiências para o repositório.
        """
        logger.info("Buscando experiências via serviço", query=query, limit=limit)
        try:
            return await self._repo.search_experiences(query=query, limit=limit)  # Pass limit to repository
        except Exception as e:
            logger.error("Erro no serviço de memória ao buscar experiências", exc_info=e)
            raise MemoryServiceError("Falha ao buscar experiências.") from e

# Padrão de Injeção de Dependência: Getter para o serviço
def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service
