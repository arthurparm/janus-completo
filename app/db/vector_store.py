import logging

import chromadb
from app.config import settings

logger = logging.getLogger(__name__)

try:
    # Inicializa o cliente ChromaDB que se conecta ao container
    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT
    )
    logger.info(f"Conexão com o ChromaDB em {settings.CHROMA_HOST}:{settings.CHROMA_PORT} estabelecida.")
except Exception as e:
    logger.error(f"Falha ao conectar com o ChromaDB: {e}", exc_info=True)
    chroma_client = None

def get_or_create_collection(collection_name: str):
    if not chroma_client:
        raise ConnectionError("Cliente ChromaDB não está disponível.")
    return chroma_client.get_or_create_collection(name=collection_name)
