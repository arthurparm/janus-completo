import logging
import asyncio
from typing import Optional

import requests
import urllib3
from qdrant_client import QdrantClient, models, AsyncQdrantClient
from qdrant_client.http.models import PayloadSchemaType

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# Circuit Breakers
_qdrant_init_cb = CircuitBreaker(failure_threshold=3, recovery_timeout=120)
_qdrant_ops_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

# Erros retriable
RETRIABLE_QDRANT_ERRORS = (
    ConnectionError,
    TimeoutError,
    requests.exceptions.RequestException,
    urllib3.exceptions.HTTPError,
)

# Clientes globais
_qdrant_client: Optional[QdrantClient] = None
_client_initialized = False
_init_error: Optional[Exception] = None

_async_qdrant_client: Optional[AsyncQdrantClient] = None

# Constantes de validação
_MIN_VECTOR_SIZE = 1
_MAX_VECTOR_SIZE = 10000
_DEFAULT_VECTOR_SIZE = 1536


def _lazy_init_client() -> Optional[QdrantClient]:
    global _qdrant_client, _client_initialized, _init_error
    if _client_initialized:
        if _init_error:
            logger.warning(f"Cliente Qdrant previamente falhou: {_init_error}")
        return _qdrant_client

    try:
        logger.info(f"Conectando ao Qdrant em {settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=10)
        client.get_collections()
        logger.info("Conexão com o Qdrant estabelecida.")
        _qdrant_client = client
        _client_initialized = True
        _init_error = None
        return _qdrant_client
    except Exception as e:
        _init_error = e
        _client_initialized = True
        logger.error(f"Falha ao conectar com o Qdrant: {e}", exc_info=True)
        return None


def get_qdrant_client() -> QdrantClient:
    client = _lazy_init_client()
    if not client:
        raise ConnectionError(f"Cliente Qdrant não está disponível. Erro: {_init_error}")
    return client


def get_async_qdrant_client() -> AsyncQdrantClient:
    """Retorna uma instância do cliente Qdrant assíncrono."""
    global _async_qdrant_client
    if _async_qdrant_client is None:
        _async_qdrant_client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=20,
        )
        logger.info("Instância do AsyncQdrantClient criada.")
    return _async_qdrant_client


def _validate_vector_size(vector_size: int) -> int:
    if not isinstance(vector_size, int) or not (_MIN_VECTOR_SIZE <= vector_size <= _MAX_VECTOR_SIZE):
        raise ValueError(f"vector_size deve estar entre {_MIN_VECTOR_SIZE} e {_MAX_VECTOR_SIZE}.")
    return vector_size


def _validate_collection_name(collection_name: str) -> str:
    if not collection_name or not collection_name.strip() or len(collection_name) > 255:
        raise ValueError("collection_name inválido.")
    import re
    # Substituir caracteres inválidos por underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', collection_name)
    if sanitized != collection_name:
        logger.warning(f"Nome da coleção '{collection_name}' sanitizado para '{sanitized}'")
    return sanitized


@resilient(
    max_attempts=3, initial_backoff=1.0, max_backoff=5.0, circuit_breaker=_qdrant_ops_cb,
    retry_on=RETRIABLE_QDRANT_ERRORS
)
def get_or_create_collection(collection_name: str, vector_size: int = _DEFAULT_VECTOR_SIZE) -> str:
    collection_name = _validate_collection_name(collection_name)
    vector_size = _validate_vector_size(vector_size)
    client = get_qdrant_client()
    try:
        collection_info = client.get_collection(collection_name=collection_name)
        if collection_info.config.params.vectors.size != vector_size:
            logger.warning(f"Tamanho do vetor da coleção '{collection_name}' difere do solicitado.")
    except Exception:
        logger.warning(f"Coleção '{collection_name}' não encontrada. Criando...")
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            logger.info(f"Coleção '{collection_name}' criada.")
            # Criar índices de payload para metadados importantes
            client.create_payload_index(collection_name=collection_name, field_name="metadata.type",
                                        field_schema=PayloadSchemaType.KEYWORD)
            client.create_payload_index(collection_name=collection_name, field_name="metadata.timestamp",
                                        field_schema=PayloadSchemaType.INTEGER)
            try:
                client.create_payload_index(collection_name=collection_name, field_name="metadata.origin",
                                            field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass
            try:
                client.create_payload_index(collection_name=collection_name, field_name="metadata.status",
                                            field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass
            logger.info(f"Índices de payload para '{collection_name}' criados em metadata.type e metadata.timestamp.")
        except Exception as create_error:
            logger.error(f"Falha ao criar coleção '{collection_name}': {create_error}", exc_info=True)
            raise ConnectionError(f"Não foi possível criar a coleção: {create_error}") from create_error
    return collection_name


async def aget_or_create_collection(collection_name: str, vector_size: int = _DEFAULT_VECTOR_SIZE) -> str:
    """Versão assíncrona para obter ou criar uma coleção no Qdrant."""
    collection_name = _validate_collection_name(collection_name)
    vector_size = _validate_vector_size(vector_size)
    async_client = get_async_qdrant_client()
    try:
        collection_info = await async_client.get_collection(collection_name=collection_name)
        if collection_info.config.params.vectors.size != vector_size:
            logger.warning(f"Tamanho do vetor da coleção '{collection_name}' difere do solicitado.")
    except Exception:
        logger.warning(f"Coleção '{collection_name}' não encontrada. Criando via async...")
        try:
            await async_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            logger.info(f"Coleção '{collection_name}' criada via async.")
            # Criar índices de payload para metadados importantes
            await async_client.create_payload_index(collection_name=collection_name, field_name="metadata.type",
                                                    field_schema=PayloadSchemaType.KEYWORD)
            await async_client.create_payload_index(collection_name=collection_name, field_name="metadata.timestamp",
                                                    field_schema=PayloadSchemaType.INTEGER)
            try:
                await async_client.create_payload_index(collection_name=collection_name, field_name="metadata.origin",
                                                        field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass
            try:
                await async_client.create_payload_index(collection_name=collection_name, field_name="metadata.status",
                                                        field_schema=PayloadSchemaType.KEYWORD)
            except Exception:
                pass
            logger.info(
                f"Índices de payload para '{collection_name}' criados em metadata.type e metadata.timestamp via async.")
        except Exception as create_error:
            logger.error(f"Falha ao criar coleção async '{collection_name}': {create_error}", exc_info=True)
            raise ConnectionError(f"Não foi possível criar a coleção async: {create_error}") from create_error
    return collection_name


@resilient(
    max_attempts=5, initial_backoff=2.0, max_backoff=10.0, circuit_breaker=_qdrant_init_cb,
    retry_on=RETRIABLE_QDRANT_ERRORS
)
def check_qdrant_readiness() -> bool:
    try:
        client = get_qdrant_client()
        client.get_collections()
        logger.info("Qdrant readiness check PASSED.")
        return True
    except Exception as e:
        logger.error(f"Qdrant readiness check FAILED: {e}", exc_info=True)
        raise ConnectionError(f"Qdrant não está pronto: {e}") from e


def reset_client():
    global _qdrant_client, _client_initialized, _init_error, _async_qdrant_client
    if _qdrant_client:
        try:
            _qdrant_client.close()
        except:
            pass
    if _async_qdrant_client:
        try:
            asyncio.run(_async_qdrant_client.close())
        except:
            pass
    _qdrant_client = None
    _client_initialized = False
    _init_error = None
    _async_qdrant_client = None
    logger.info("Clientes Qdrant resetados.")


def get_collection_info(collection_name: str) -> dict:
    collection_name = _validate_collection_name(collection_name)
    client = get_qdrant_client()
    try:
        info = client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "vector_size": info.config.params.vectors.size,
            "points_count": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações da coleção '{collection_name}': {e}")
        raise
