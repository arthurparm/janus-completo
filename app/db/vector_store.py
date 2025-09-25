# app/db/vector_store.py
import logging

import requests
import urllib3
from qdrant_client import QdrantClient, models

from app.config import settings
from app.core.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

qdrant_client = None
qdrant_cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
# --- MELHORIA: ESPECIFICAR EXCEÇÕES RETRIÁVEIS ---
RETRIABLE_QDRANT_ERRORS = (
    ConnectionError,
    TimeoutError,
    requests.exceptions.RequestException,
    urllib3.exceptions.HTTPError,
)  # Erros de rede comuns para retry

try:
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )
    # --- MELHORIA: VERIFICAÇÃO DE READINESS CORRETA ---
    qdrant_client.get_collections()
    logger.info(f"Conexão com o Qdrant em {settings.QDRANT_HOST}:{settings.QDRANT_PORT} estabelecida com sucesso.")
except Exception as e:
    logger.error(f"Falha ao conectar com o Qdrant durante a inicialização: {e}", exc_info=True)
    qdrant_client = None


@resilient(circuit_breaker=qdrant_cb, retry_on=RETRIABLE_QDRANT_ERRORS)
def get_or_create_collection(collection_name: str, vector_size: int = 1536):
    if not qdrant_client:
        raise ConnectionError("Cliente Qdrant não está disponível.")
    try:
        qdrant_client.get_collection(collection_name=collection_name)
    except Exception:
        logger.warning(f"Coleção '{collection_name}' não encontrada. Criando nova coleção...")
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        logger.info(f"Coleção '{collection_name}' criada com sucesso.")
    return collection_name


@resilient(max_attempts=5, initial_backoff=2, retry_on=RETRIABLE_QDRANT_ERRORS)
def check_qdrant_readiness() -> bool:
    """Verifica a prontidão do Qdrant chamando uma operação leve."""
    if not qdrant_client:
        raise ConnectionError("Cliente Qdrant não está disponível.")
    # --- MELHORIA: USA get_collections() PARA VERIFICAÇÃO ---
    qdrant_client.get_collections()
    logger.info("Qdrant readiness check PASSED.")
    return True


# Para manter a compatibilidade com o resto do código, podemos expor o cliente
def get_qdrant_client() -> QdrantClient:
    if not qdrant_client:
        raise ConnectionError("Cliente Qdrant não está disponível.")
    return qdrant_client
