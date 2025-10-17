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

    async def recall_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando experiências filtradas", query=query, filters=filters, limit=limit)
        try:
            return await self._repo.search_filtered(query=query, filters=filters, limit=limit)
        except Exception as e:
            logger.error("Erro no serviço ao buscar filtrado", exc_info=e)
            raise MemoryServiceError("Falha na busca filtrada.") from e

    async def recall_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando por janela temporal", query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit)
        try:
            return await self._repo.search_by_timeframe(query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit)
        except Exception as e:
            logger.error("Erro no serviço ao buscar por janela temporal", exc_info=e)
            raise MemoryServiceError("Falha na busca por janela temporal.") from e

    async def recall_recent_failures(self, limit: Optional[int] = None, timeframe_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando falhas recentes", limit=limit, timeframe_seconds=timeframe_seconds)
        try:
            return await self._repo.search_recent_failures(limit=limit, timeframe_seconds=timeframe_seconds)
        except Exception as e:
            logger.error("Erro no serviço ao buscar falhas recentes", exc_info=e)
            raise MemoryServiceError("Falha na busca de falhas recentes.") from e

# Padrão de Injeção de Dependência: Getter para o serviço
def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service
