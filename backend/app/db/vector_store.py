import re
import uuid
from dataclasses import dataclass

import requests
import structlog
import urllib3
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PayloadSchemaType

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient

logger = structlog.get_logger(__name__)

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
_DEFAULT_INDEXING_THRESHOLD = 200
_DEFAULT_FULL_SCAN_THRESHOLD = 200


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    hnsw_m: int = 32
    ef_construct: int = 200
    full_scan_threshold: int = _DEFAULT_FULL_SCAN_THRESHOLD
    indexing_threshold: int = _DEFAULT_INDEXING_THRESHOLD
    use_quantization: bool = True
    payload_indexes: dict[str, PayloadSchemaType] | None = None


_LEGACY_USER_COLLECTION_PATTERN = re.compile(r"^user_[A-Za-z0-9_-]+$")


def _sanitize_user_fragment(user_id: str) -> str:
    value = str(user_id or "").strip()
    if not value:
        raise ValueError("user_id inválido.")
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
    if not sanitized:
        raise ValueError("user_id inválido.")
    return sanitized


def build_user_chat_collection_name(user_id: str) -> str:
    return f"user_chat_{_sanitize_user_fragment(user_id)}"


def build_user_docs_collection_name(user_id: str) -> str:
    return f"user_docs_{_sanitize_user_fragment(user_id)}"


def build_user_memory_collection_name(user_id: str) -> str:
    return f"user_memory_{_sanitize_user_fragment(user_id)}"


def build_user_secret_collection_name(user_id: str) -> str:
    return f"user_secret_{_sanitize_user_fragment(user_id)}"


def get_user_collection_names(user_id: str) -> dict[str, str]:
    return {
        "chat": build_user_chat_collection_name(user_id),
        "docs": build_user_docs_collection_name(user_id),
        "memory": build_user_memory_collection_name(user_id),
        "secret": build_user_secret_collection_name(user_id),
    }


def build_deterministic_point_id(namespace: str, *parts: object) -> str:
    joined = ":".join(str(part or "").strip() for part in parts)
    seed = f"{namespace}:{joined}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _infer_collection_spec(collection_name: str) -> CollectionSpec:
    episodic_indexes = {
        "metadata.type": PayloadSchemaType.KEYWORD,
        "metadata.origin": PayloadSchemaType.KEYWORD,
        "metadata.source_kind": PayloadSchemaType.KEYWORD,
        "metadata.content_kind": PayloadSchemaType.KEYWORD,
        "metadata.consolidation_status": PayloadSchemaType.KEYWORD,
        "metadata.neo4j_sync_status": PayloadSchemaType.KEYWORD,
        "metadata.file_path": PayloadSchemaType.KEYWORD,
        "metadata.sha_after": PayloadSchemaType.KEYWORD,
        "metadata.user_id": PayloadSchemaType.KEYWORD,
        "metadata.conversation_id": PayloadSchemaType.KEYWORD,
        "metadata.memory_key": PayloadSchemaType.KEYWORD,
        "metadata.summary_version": PayloadSchemaType.KEYWORD,
        "metadata.local_only": PayloadSchemaType.BOOL,
        "metadata.strong_memory": PayloadSchemaType.BOOL,
        "metadata.captured_at": PayloadSchemaType.INTEGER,
        "metadata.timestamp": PayloadSchemaType.INTEGER,
    }
    if collection_name == getattr(settings, "QDRANT_COLLECTION_EPISODIC", "janus_episodic_memory"):
        return CollectionSpec(
            name=collection_name,
            hnsw_m=int(getattr(settings, "QDRANT_EPISODIC_HNSW_M", 32)),
            ef_construct=int(
                getattr(settings, "QDRANT_EPISODIC_EF_CONSTRUCT", 200)
            ),
            full_scan_threshold=int(
                getattr(
                    settings,
                    "QDRANT_EPISODIC_FULL_SCAN_THRESHOLD",
                    _DEFAULT_FULL_SCAN_THRESHOLD,
                )
            ),
            indexing_threshold=int(
                getattr(
                    settings,
                    "QDRANT_EPISODIC_INDEXING_THRESHOLD",
                    _DEFAULT_INDEXING_THRESHOLD,
                )
            ),
            payload_indexes=episodic_indexes,
        )
    if collection_name.startswith("user_chat_"):
        return CollectionSpec(
            name=collection_name,
            payload_indexes={
                "metadata.type": PayloadSchemaType.KEYWORD,
                "metadata.user_id": PayloadSchemaType.KEYWORD,
                "metadata.session_id": PayloadSchemaType.KEYWORD,
                "metadata.conversation_id": PayloadSchemaType.KEYWORD,
                "metadata.role": PayloadSchemaType.KEYWORD,
                "metadata.origin": PayloadSchemaType.KEYWORD,
                "metadata.timestamp": PayloadSchemaType.INTEGER,
            },
        )
    if collection_name.startswith("user_docs_"):
        return CollectionSpec(
            name=collection_name,
            payload_indexes={
                "metadata.type": PayloadSchemaType.KEYWORD,
                "metadata.user_id": PayloadSchemaType.KEYWORD,
                "metadata.doc_id": PayloadSchemaType.KEYWORD,
                "metadata.file_name": PayloadSchemaType.KEYWORD,
                "metadata.content_hash": PayloadSchemaType.KEYWORD,
                "metadata.status": PayloadSchemaType.KEYWORD,
                "metadata.conversation_id": PayloadSchemaType.KEYWORD,
                "metadata.origin": PayloadSchemaType.KEYWORD,
                "metadata.timestamp": PayloadSchemaType.INTEGER,
            },
        )
    if collection_name.startswith("user_memory_"):
        return CollectionSpec(
            name=collection_name,
            payload_indexes={
                "metadata.type": PayloadSchemaType.KEYWORD,
                "metadata.memory_class": PayloadSchemaType.KEYWORD,
                "metadata.user_id": PayloadSchemaType.KEYWORD,
                "metadata.conversation_id": PayloadSchemaType.KEYWORD,
                "metadata.session_id": PayloadSchemaType.KEYWORD,
                "metadata.origin": PayloadSchemaType.KEYWORD,
                "metadata.status": PayloadSchemaType.KEYWORD,
                "metadata.active": PayloadSchemaType.BOOL,
                "metadata.preference_kind": PayloadSchemaType.KEYWORD,
                "metadata.recall_policy": PayloadSchemaType.KEYWORD,
                "metadata.retention_policy": PayloadSchemaType.KEYWORD,
                "metadata.sensitivity": PayloadSchemaType.KEYWORD,
                "metadata.scope": PayloadSchemaType.KEYWORD,
                "metadata.timestamp": PayloadSchemaType.INTEGER,
            },
        )
    if collection_name.startswith("user_secret_"):
        return CollectionSpec(
            name=collection_name,
            payload_indexes={
                "metadata.user_id": PayloadSchemaType.KEYWORD,
                "metadata.conversation_id": PayloadSchemaType.KEYWORD,
                "metadata.secret_type": PayloadSchemaType.KEYWORD,
                "metadata.secret_label": PayloadSchemaType.KEYWORD,
                "metadata.secret_scope": PayloadSchemaType.KEYWORD,
                "metadata.recall_policy": PayloadSchemaType.KEYWORD,
                "metadata.sensitivity": PayloadSchemaType.KEYWORD,
                "metadata.active": PayloadSchemaType.BOOL,
                "metadata.timestamp": PayloadSchemaType.INTEGER,
            },
        )
    if _LEGACY_USER_COLLECTION_PATTERN.match(collection_name):
        return CollectionSpec(
            name=collection_name,
            payload_indexes={
                "metadata.type": PayloadSchemaType.KEYWORD,
                "metadata.user_id": PayloadSchemaType.KEYWORD,
                "metadata.origin": PayloadSchemaType.KEYWORD,
                "metadata.status": PayloadSchemaType.KEYWORD,
                "metadata.timestamp": PayloadSchemaType.INTEGER,
            },
        )
    return CollectionSpec(name=collection_name, payload_indexes={"metadata.timestamp": PayloadSchemaType.INTEGER})

def _resolve_qdrant_api_key() -> str | None:
    api_key = getattr(settings, "QDRANT_API_KEY", None)
    if hasattr(api_key, "get_secret_value"):
        api_key = api_key.get_secret_value()
    return str(api_key).strip() if api_key else None


def get_async_qdrant_client() -> AsyncQdrantClient:
    """Retorna uma instância do cliente Qdrant assíncrono."""
    global _async_qdrant_client
    if _async_qdrant_client is None:
        client_kwargs: dict[str, object] = {
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
            "timeout": 20,
            "https": bool(getattr(settings, "QDRANT_HTTPS", False)),
        }
        api_key = _resolve_qdrant_api_key()
        if api_key:
            client_kwargs["api_key"] = api_key
        _async_qdrant_client = AsyncQdrantClient(**client_kwargs)
        logger.info("Instância do AsyncQdrantClient criada.")
    return _async_qdrant_client


async def async_count_points(
    client: AsyncQdrantClient, collection_name: str, qfilter: models.Filter, exact: bool = True
) -> int:
    """Conta pontos usando a API canônica `count` do cliente Qdrant."""
    resp = await client.count(collection_name=collection_name, count_filter=qfilter, exact=exact)
    return int(getattr(resp, "count", 0) or 0)


async def _ensure_collection_tuning(
    client: AsyncQdrantClient, collection_name: str, spec: CollectionSpec
) -> None:
    try:
        await client.update_collection(
            collection_name=collection_name,
            hnsw_config=models.HnswConfigDiff(
                m=spec.hnsw_m,
                ef_construct=spec.ef_construct,
                full_scan_threshold=spec.full_scan_threshold,
            ),
            optimizer_config=models.OptimizersConfigDiff(
                indexing_threshold=spec.indexing_threshold
            ),
        )
    except Exception as exc:
        logger.warning(
            "log_warning",
            message=f"Falha ao ajustar tuning da coleção '{collection_name}': {exc}",
        )


async def _ensure_payload_indexes(
    client: AsyncQdrantClient, collection_name: str, spec: CollectionSpec
) -> None:
    for field_name, schema in (spec.payload_indexes or {}).items():
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema,
            )
        except Exception as exc:
            logger.debug(
                "qdrant_payload_index_ensure_failed",
                field_name=field_name,
                collection=collection_name,
                error=str(exc),
            )


async def aensure_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    vector_size: int = _DEFAULT_VECTOR_SIZE,
) -> str:
    collection_name = _validate_collection_name(collection_name)
    vector_size = _validate_vector_size(vector_size)
    spec = _infer_collection_spec(collection_name)
    try:
        collection_info = await client.get_collection(collection_name=collection_name)
        if collection_info.config.params.vectors.size != vector_size:
            logger.warning(
                "log_warning",
                message=f"Tamanho do vetor da coleção '{collection_name}' difere do solicitado.",
            )
        await _ensure_collection_tuning(client, collection_name, spec)
        await _ensure_payload_indexes(client, collection_name, spec)
        return collection_name
    except UnexpectedResponse as get_error:
        if get_error.status_code != 404:
            logger.error(
                "log_error",
                message=f"Falha ao consultar coleção async '{collection_name}': {get_error}",
                exc_info=True,
            )
            raise ConnectionError(
                f"Não foi possível consultar a coleção async: {get_error}"
            ) from get_error
    except Exception as get_error:
        logger.error(
            "log_error",
            message=f"Falha inesperada ao consultar coleção async '{collection_name}': {get_error}",
            exc_info=True,
        )
        raise ConnectionError(
            f"Não foi possível consultar a coleção async: {get_error}"
        ) from get_error

    logger.warning("log_warning", message=f"Coleção '{collection_name}' não encontrada. Criando via async...")
    try:
        create_kwargs: dict[str, object] = {
            "collection_name": collection_name,
            "vectors_config": models.VectorParams(
                size=vector_size, distance=models.Distance.COSINE
            ),
            "hnsw_config": models.HnswConfigDiff(
                m=spec.hnsw_m,
                ef_construct=spec.ef_construct,
                full_scan_threshold=spec.full_scan_threshold,
            ),
            "optimizers_config": models.OptimizersConfigDiff(
                indexing_threshold=spec.indexing_threshold
            ),
        }
        if spec.use_quantization:
            create_kwargs["quantization_config"] = models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            )
        await client.create_collection(**create_kwargs)
        logger.info("log_info", message=f"Coleção '{collection_name}' criada via async.")
    except UnexpectedResponse as create_error:
        if create_error.status_code == 409:
            logger.info(
                "log_info",
                message=f"Coleção '{collection_name}' já foi criada por outra requisição (409). Continuando.",
            )
        else:
            logger.error(
                "log_error",
                message=f"Falha ao criar coleção async '{collection_name}': {create_error}",
                exc_info=True,
            )
            raise ConnectionError(
                f"Não foi possível criar a coleção async: {create_error}"
            ) from create_error
    except Exception as create_error:
        logger.error(
            "log_error",
            message=f"Falha ao criar coleção async '{collection_name}': {create_error}",
            exc_info=True,
        )
        raise ConnectionError(
            f"Não foi possível criar a coleção async: {create_error}"
        ) from create_error

    await _ensure_collection_tuning(client, collection_name, spec)
    await _ensure_payload_indexes(client, collection_name, spec)
    return collection_name


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
        logger.warning("log_warning", message=f"Nome da coleção '{collection_name}' sanitizado para '{sanitized}'")
    return sanitized


async def aget_or_create_collection(
    collection_name: str, vector_size: int = _DEFAULT_VECTOR_SIZE
) -> str:
    """Versão assíncrona para obter ou criar uma coleção no Qdrant."""
    async_client = get_async_qdrant_client()
    return await aensure_collection(async_client, collection_name=collection_name, vector_size=vector_size)


async def check_qdrant_readiness() -> bool:
    """Versão assíncrona do readiness check."""
    try:
        async_client = get_async_qdrant_client()
        await async_client.get_collections()
        logger.info("Qdrant readiness check PASSED.")
        return True
    except Exception as e:
        logger.error("log_error", message=f"Qdrant readiness check FAILED: {e}", exc_info=True)
        raise ConnectionError(f"Qdrant não está pronto: {e}") from e


async def reset_client() -> None:
    """Fecha e limpa o cliente Qdrant de forma totalmente assíncrona."""
    global _async_qdrant_client
    if _async_qdrant_client:
        try:
            await _async_qdrant_client.close()
        except Exception as e:
            logger.warning("log_warning", message=f"Error closing async Qdrant client: {e}")
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
        logger.info("log_info", message=f"Pontos deletados de '{collection_name}' com filtro: {filter_conditions}")
    except Exception as e:
        logger.error("log_error", message=f"Erro ao deletar pontos de '{collection_name}': {e}", exc_info=True)
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
        logger.error("log_error", message=f"Erro ao obter informações da coleção '{collection_name}' (async): {e}")
        raise


async def aget_total_points(collection_names: list[str]) -> int:
    total = 0
    for collection_name in collection_names:
        try:
            info = await aget_collection_info(collection_name)
            total += int(info.get("points_count") or 0)
        except Exception:
            continue
    return total
