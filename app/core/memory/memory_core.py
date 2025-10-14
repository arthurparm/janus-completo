import structlog
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient, models

from app.config import settings
from app.models.schemas import Experience, VectorCollection  # Importa o Enum

logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Gerencia a conexão e as operações com o banco de dados vetorial (Qdrant).
    """
    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = VectorCollection.EPISODIC_MEMORY  # Usa o Enum

    async def initialize(self):
        """Garante que a coleção exista no Qdrant."""
        try:
            collections = await self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Coleção '{self.collection_name}' não encontrada. Criando nova coleção...")
                await self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
                )
                logger.info("Coleção criada com sucesso.")
            else:
                logger.info(f"Coleção '{self.collection_name}' já existe.")
        except Exception as e:
            logger.error("Falha ao inicializar o MemoryCore (Qdrant)", exc_info=e)
            raise

    async def amemorize(self, experience: Experience):
        """Adiciona uma experiência à memória (upsert)."""
        point = models.PointStruct(
            id=experience.id,
            payload=experience.dict(),
            # O vetor real seria gerado por um modelo de embedding aqui
        )
        await self.client.upsert_points(collection_name=self.collection_name, points=[point], wait=True)

    async def arecall(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca por experiências na memória."""
        query_vector = [0.0] * 384  # Simulação de embedding
        hits = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True
        )
        return [{"id": hit.id, "content": hit.payload.get('content'), "metadata": hit.payload.get('metadata'),
                 "score": hit.score} for hit in hits]

    async def asearch(self, query_text: str, filters: Dict[str, Any], limit: int) -> List[Experience]:
        # Placeholder para busca com filtros
        return []


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_memory_db_instance: Optional[MemoryCore] = None


async def initialize_memory_db():
    global _memory_db_instance
    if _memory_db_instance is None:
        _memory_db_instance = MemoryCore()
        await _memory_db_instance.initialize()


async def close_memory_db():
    pass


async def get_memory_db() -> MemoryCore:
    if _memory_db_instance is None:
        await initialize_memory_db()
    return _memory_db_instance
