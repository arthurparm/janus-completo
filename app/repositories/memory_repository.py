import structlog
from typing import List, Dict, Any
from fastapi import Depends

from app.core.memory.memory_core import MemoryCore, get_memory_db
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

class MemoryRepository:
    """
    Camada de Repositório para a Memória Episódica (Qdrant).
    Recebe sua dependência de banco de dados via DI.
    """

    def __init__(self, db: MemoryCore):
        self._db = db

    async def save_experience(self, experience: Experience):
        """Salva uma única experiência no banco de dados vetorial."""
        logger.debug("Salvando experiência no repositório de memória", experience_id=experience.id)
        try:
            await self._db.amemorize(experience)
        except Exception as e:
            logger.error("Erro no repositório ao salvar experiência", exc_info=e)
            raise

    async def search_experiences(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca por experiências no banco de dados vetorial."""
        logger.debug("Buscando experiências no repositório de memória", query=query, limit=limit)
        try:
            return await self._db.arecall(query=query, limit=limit)
        except Exception as e:
            logger.error("Erro no repositório ao buscar experiências", exc_info=e)
            raise


# Padrão de Injeção de Dependência: Getter para o repositório
def get_memory_repository(db: MemoryCore = Depends(get_memory_db)) -> MemoryRepository:
    return MemoryRepository(db)
