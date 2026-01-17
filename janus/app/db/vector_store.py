import logging

import requests
import urllib3
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import PayloadSchemaType

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient

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

# Cliente global async
_async_qdrant_client: AsyncQdrantClient | None = None

# Constantes de validação
_MIN_VECTOR_SIZE = 1
_MAX_VECTOR_SIZE = 10000
_DEFAULT_VECTOR_SIZE = 1536


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
    if not isinstance(vector_size, int) or not (
        _MIN_VECTOR_SIZE <= vector_size <= _MAX_VECTOR_SIZE
    ):
        raise ValueError(f"vector_size deve estar entre {_MIN_VECTOR_SIZE} e {_MAX_VECTOR_SIZE}.")
    return vector_size


def _validate_collection_name(collection_name: str) -> str:
    if not collection_name or not collection_name.strip() or len(collection_name) > 255:
        raise ValueError("collection_name inválido.")
    import re

    # Substituir caracteres inválidos por underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", collection_name)
    if sanitized != collection_name:
        logger.warning(f"Nome da coleção '{collection_name}' sanitizado para '{sanitized}'")
    return sanitized


async def aget_or_create_collection(
    collection_name: str, vector_size: int = _DEFAULT_VECTOR_SIZE
) -> str:
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
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
                # EVOLUTION: Scalar Quantization (Int8) for 4x memory compression
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8,
                        quantile=0.99,
                        always_ram=True,
                    )
                ),
                # EVOLUTION: Optimized HNSW for scale
                hnsw_config=models.HnswConfigDiff(
                    m=32,
                    ef_construct=200,
                    full_scan_threshold=10000,
                ),
            )
            logger.info(f"Coleção '{collection_name}' criada via async.")
            # Criar índices de payload para metadados importantes
            await async_client.create_payload_index(
                collection_name=collection_name,
                field_name="metadata.type",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await async_client.create_payload_index(
                collection_name=collection_name,
                field_name="metadata.timestamp",
                field_schema=PayloadSchemaType.INTEGER,
            )
            try:
                await async_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="metadata.origin",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as e:
                logger.warning(f"Failed to create async 'origin' index for {collection_name}: {e}")
            try:
                await async_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="metadata.status",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as e:
                logger.warning(f"Failed to create async 'status' index for {collection_name}: {e}")
            logger.info(
                f"Índices de payload para '{collection_name}' criados em metadata.type e metadata.timestamp via async."
            )
        except Exception as create_error:
            logger.error(
                f"Falha ao criar coleção async '{collection_name}': {create_error}", exc_info=True
            )
            raise ConnectionError(
                f"Não foi possível criar a coleção async: {create_error}"
            ) from create_error
    return collection_name


async def check_qdrant_readiness() -> bool:
    """Versão assíncrona do readiness check."""
    try:
        async_client = get_async_qdrant_client()
        await async_client.get_collections()
        logger.info("Qdrant readiness check PASSED.")
        return True
    except Exception as e:
        logger.error(f"Qdrant readiness check FAILED: {e}", exc_info=True)
        raise ConnectionError(f"Qdrant não está pronto: {e}") from e


async def reset_client() -> None:
    """Fecha e limpa o cliente Qdrant de forma totalmente assíncrona."""
    global _async_qdrant_client
    if _async_qdrant_client:
        try:
            await _async_qdrant_client.close()
        except Exception as e:
            logger.warning(f"Error closing async Qdrant client: {e}")
    _async_qdrant_client = None
    logger.info("Cliente Qdrant async resetado.")



async def delete_points_by_filter(collection_name: str, filter_conditions: dict) -> None:
    """Deleta pontos que correspondem ao filtro especificado."""
    collection_name = _validate_collection_name(collection_name)
    client = get_async_qdrant_client()
    try:
        q_filter = models.Filter(
            must=[
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
        )
        await client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(filter=q_filter)
        )
        logger.info(f"Pontos deletados de '{collection_name}' com filtro: {filter_conditions}")
    except Exception as e:
        logger.error(f"Erro ao deletar pontos de '{collection_name}': {e}", exc_info=True)
        raise

async def aget_collection_info(collection_name: str) -> dict:
    """Versão assíncrona para obter informações da coleção."""
    collection_name = _validate_collection_name(collection_name)
    client = get_async_qdrant_client()
    try:
        info = await client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "vector_size": info.config.params.vectors.size,
            "points_count": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações da coleção '{collection_name}' (async): {e}")
        raise
