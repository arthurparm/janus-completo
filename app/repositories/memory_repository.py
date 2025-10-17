import structlog
from typing import List, Dict, Any, Optional
from fastapi import Depends

from app.core.memory.memory_core import get_memory_db
from app.core.protocols import MemoryDBProtocol
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

class MemoryRepository:
    """
    Camada de Repositório para a Memória Episódica (Qdrant).
    Recebe sua dependência de banco de dados via DI.
    """

    def __init__(self, db: MemoryDBProtocol):
        self._db = db

    async def save_experience(self, experience: Experience):
        """Salva uma única experiência no banco de dados vetorial."""
        logger.debug("Salvando experiência no repositório de memória", experience_id=experience.id)
        try:
            await self._db.amemorize(experience)
        except Exception as e:
            logger.error("Erro no repositório ao salvar experiência", exc_info=e)
            raise

    async def search_experiences(self, query: str, limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """Busca por experiências no banco de dados vetorial."""
        logger.debug("Buscando experiências no repositório de memória", query=query, limit=limit, min_score=min_score)
        try:
            return await self._db.arecall(query=query, limit=limit, min_score=min_score)
        except Exception as e:
            logger.error("Erro no repositório ao buscar experiências", exc_info=e)
            raise

    async def search_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Busca filtrada no repositório de memória", query=query, filters=filters, limit=limit, min_score=min_score)
        try:
            return await self._db.arecall_filtered(query=query, filters=filters, limit=limit, min_score=min_score)
        except Exception as e:
            logger.error("Erro no repositório ao buscar com filtros", exc_info=e)
            raise

    async def search_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Busca por janela temporal", query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit, min_score=min_score)
        try:
            return await self._db.arecall_by_timeframe(query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit, min_score=min_score)
        except Exception as e:
            logger.error("Erro no repositório ao buscar por janela temporal", exc_info=e)
            raise

    async def search_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Busca falhas recentes", limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        try:
            return await self._db.arecall_recent_failures(limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        except Exception as e:
            logger.error("Erro no repositório ao buscar falhas recentes", exc_info=e)
            raise

    async def search_recent_lessons(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Busca lições recentes", limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        try:
            return await self._db.arecall_recent_lessons(limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        except Exception as e:
            logger.error("Erro no repositório ao buscar lições recentes", exc_info=e)
            raise


# Padrão de Injeção de Dependência: Getter para o repositório
def get_memory_repository(db: MemoryDBProtocol = Depends(get_memory_db)) -> MemoryRepository:
    return MemoryRepository(db)
