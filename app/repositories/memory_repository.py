import structlog
from typing import List, Dict, Any

from app.core.memory.memory_core import memory_core
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)


class MemoryRepository:
    """
    Camada de Repositório para a Memória Episódica (Qdrant).
    Abstrai todas as interações diretas com o `memory_core`.
    """

    async def save_experience(self, experience: Experience):
        """Salva uma única experiência no banco de dados vetorial."""
        logger.debug("Salvando experiência no repositório de memória", experience_id=experience.id)
        try:
            await memory_core.amemorize(experience)
        except Exception as e:
            logger.error("Erro no repositório ao salvar experiência", exc_info=e)
            # Em um caso real, poderíamos ter uma exceção de repositório mais específica
            raise

    async def search_experiences(self, query: str) -> List[Dict[str, Any]]:
        """Busca por experiências no banco de dados vetorial."""
        logger.debug("Buscando experiências no repositório de memória", query=query)
        try:
            return await memory_core.arecall(query=query)
        except Exception as e:
            logger.error("Erro no repositório ao buscar experiências", exc_info=e)
            raise


# Instância única do repositório
memory_repository = MemoryRepository()
