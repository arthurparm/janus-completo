import structlog
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient, models

from app.config import settings
from app.models.schemas import Experience, VectorCollection

logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Gerencia a conexão e as operações com o banco de dados vetorial (Qdrant).
    """

    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = VectorCollection.EPISODIC_MEMORY.value

    async def initialize(self):
        """
        Garante que a coleção exista no Qdrant.
        """
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Coleção '{self.collection_name}' não encontrada. Criando nova coleção...")
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
                )
                logger.info("Coleção criada com sucesso.")
            else:
                logger.info(f"Coleção '{self.collection_name}' já existe.")
        except Exception as e:
            logger.error("Falha ao inicializar o MemoryCore (Qdrant)", exc_info=e)
            raise

    async def amemorize(self, experience: Experience):
        """
        Adiciona uma experiência à memória (upsert).
        """
        point = models.PointStruct(
            id=experience.id,
            payload=experience.dict(),
            vector=[0.0] * 1536
        )
        self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)

    async def arecall(self, query: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        """
        Busca por experiências na memória.
        """
        query_vector = [0.0] * 1536
        effective_limit = limit if limit is not None else 10
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=effective_limit,
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


# --- Compatibilidade com código legado ---
memory_core = _memory_db_instance


# --- Funções de criptografia (stub) ---
def decrypt_text(encrypted_text: str, key: str) -> str:
    """
    Stub para descriptografia de texto.
    """
    logger.warning("decrypt_text chamado mas não implementado - retornando texto sem descriptografia")
    return encrypted_text
