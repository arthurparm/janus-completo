# app/db/vector_store.py
import logging
from qdrant_client import QdrantClient, models
from app.config import settings

logger = logging.getLogger(__name__)

qdrant_client = None
try:
    # Inicializa o cliente Qdrant que se conecta ao container
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        # api_key=settings.QDRANT_API_KEY.get_secret_value() if settings.QDRANT_API_KEY else None, # Descomente se usar Qdrant Cloud
    )
    # Testa a conexão de forma leve chamando uma listagem de coleções
    qdrant_client.get_collections()
    logger.info(f"Conexão com o Qdrant em {settings.QDRANT_HOST}:{settings.QDRANT_PORT} estabelecida com sucesso.")
except Exception as e:
    logger.error(f"Falha ao conectar com o Qdrant: {e}", exc_info=True)
    qdrant_client = None

def get_or_create_collection(collection_name: str, vector_size: int = 1536):  # Exemplo de tamanho para text-embedding-ada-002
    """
    Obtém uma coleção do Qdrant ou a cria se não existir.
    """
    if not qdrant_client:
        raise ConnectionError("Cliente Qdrant não está disponível.")

    try:
        # Verifica se a coleção já existe
        qdrant_client.get_collection(collection_name=collection_name)
        logger.info(f"Coleção '{collection_name}' já existe.")
    except Exception:
        # Cria a coleção se ela não existir
        logger.info(f"Coleção '{collection_name}' não encontrada. Criando nova coleção...")
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        logger.info(f"Coleção '{collection_name}' criada com sucesso.")

    return collection_name  # Retorna o nome para ser usado pelo cliente

# Para manter a compatibilidade com o resto do código, podemos expor o cliente
def get_qdrant_client() -> QdrantClient:
    if not qdrant_client:
        raise ConnectionError("Cliente Qdrant não está disponível.")
    return qdrant_client
