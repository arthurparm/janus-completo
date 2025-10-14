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
        self.collection_name = VectorCollection.EPISODIC_MEMORY.value  # Usa o valor do Enum

    async def initialize(self):
        """
        Garante que a coleção exista no Qdrant.
        Atualizado para usar a dimensão de vetor correta (1536).
        """
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Coleção '{self.collection_name}' não encontrada. Criando nova coleção...")
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
                    # Alterado para 1536
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
        NOTA: O vetor real deve ser gerado por um modelo de embedding de 1536 dimensões.
        """
        point = models.PointStruct(
            id=experience.id,
            payload=experience.dict(),
            # O vetor real seria gerado por um modelo de embedding aqui
            # Exemplo: vector=embedding_model.encode(experience.content).tolist()
            # Para fins de teste, usaremos um vetor de zeros de 1536 dimensões.
            vector=[0.0] * 1536  # Alterado para 1536
        )
        # QdrantClient.upsert_points is an async method, so await is correct here.
        await self.client.upsert_points(collection_name=self.collection_name, points=[point], wait=True)

    async def arecall(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca por experiências na memória.
        Atualizado para usar um vetor de consulta de 1536 dimensões.
        """
        query_vector = [0.0] * 1536  # Simulação de embedding - Alterado para 1536
        # Removed 'await' as QdrantClient.search is a synchronous method.
        hits = self.client.search(
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


# --- Compatibilidade com código legado ---
# Exportar uma referência para a instância singleton (para imports legados)
# NOTA: Esta é uma referência que será None até initialize_memory_db() ser chamada
memory_core = _memory_db_instance


# --- Funções de criptografia (stub) ---
def decrypt_text(encrypted_text: str, key: str) -> str:
    """
    Stub para descriptografia de texto.
    TODO: Implementar criptografia real quando necessário.
    Por enquanto, retorna o texto sem modificação.
    """
    logger.warning("decrypt_text chamado mas não implementado - retornando texto sem descriptografia")
    return encrypted_text
