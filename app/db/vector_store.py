import logging
import time
from typing import Optional

import requests
import urllib3
from qdrant_client import QdrantClient, models

from app.config import settings
from app.core.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# Circuit Breakers específicos por operação
_qdrant_init_cb = CircuitBreaker(failure_threshold=3, recovery_timeout=120)
_qdrant_ops_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

# Erros retriable
RETRIABLE_QDRANT_ERRORS = (
    ConnectionError,
    TimeoutError,
    requests.exceptions.RequestException,
    urllib3.exceptions.HTTPError,
)

# Cliente global (inicializado sob demanda)
_qdrant_client: Optional[QdrantClient] = None
_client_initialized = False
_init_error: Optional[Exception] = None

# Constantes de validação
_MIN_VECTOR_SIZE = 1
_MAX_VECTOR_SIZE = 10000
_DEFAULT_VECTOR_SIZE = 1536


def _lazy_init_client() -> Optional[QdrantClient]:
    """
    Inicializa o cliente Qdrant de forma lazy e thread-safe.

    Returns:
        Cliente Qdrant ou None se inicialização falhar
    """
    global _qdrant_client, _client_initialized, _init_error

    if _client_initialized:
        if _init_error:
            logger.warning(
                f"Cliente Qdrant previamente falhou ao inicializar: {_init_error}. "
                f"Retornando None."
            )
        return _qdrant_client

    try:
        logger.info(
            f"Tentando conectar ao Qdrant em {settings.QDRANT_HOST}:{settings.QDRANT_PORT}..."
        )

        client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=10,  # Timeout explícito
        )

        # Health check com timeout
        try:
            collections = client.get_collections()
            logger.info(
                f"Conexão com o Qdrant estabelecida com sucesso. "
                f"Coleções disponíveis: {len(collections.collections)}"
            )
        except Exception as e:
            logger.error(f"Health check do Qdrant falhou: {e}")
            raise ConnectionError(f"Qdrant não está acessível: {e}") from e

        _qdrant_client = client
        _client_initialized = True
        _init_error = None

        return _qdrant_client

    except Exception as e:
        _init_error = e
        _client_initialized = True  # Marca como tentado
        logger.error(
            f"Falha ao conectar com o Qdrant: {e}. "
            f"Operações de vector store ficarão indisponíveis.",
            exc_info=True
        )
        return None


def get_qdrant_client() -> QdrantClient:
    """
    Obtém o cliente Qdrant, inicializando se necessário.

    Returns:
        Cliente Qdrant configurado

    Raises:
        ConnectionError: Se o cliente não estiver disponível
    """
    client = _lazy_init_client()
    if not client:
        raise ConnectionError(
            f"Cliente Qdrant não está disponível. "
            f"Verifique se o Qdrant está rodando em {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. "
            f"Erro original: {_init_error}"
        )
    return client


def _validate_vector_size(vector_size: int) -> int:
    """
    Valida o tamanho do vetor.

    Args:
        vector_size: Tamanho proposto do vetor

    Returns:
        Tamanho validado do vetor

    Raises:
        ValueError: Se o tamanho for inválido
    """
    if not isinstance(vector_size, int):
        raise ValueError(f"vector_size deve ser int, recebido: {type(vector_size).__name__}")

    if vector_size < _MIN_VECTOR_SIZE or vector_size > _MAX_VECTOR_SIZE:
        raise ValueError(
            f"vector_size deve estar entre {_MIN_VECTOR_SIZE} e {_MAX_VECTOR_SIZE}. "
            f"Recebido: {vector_size}"
        )

    return vector_size


def _validate_collection_name(collection_name: str) -> str:
    """
    Valida o nome da coleção.

    Args:
        collection_name: Nome da coleção

    Returns:
        Nome validado

    Raises:
        ValueError: Se o nome for inválido
    """
    if not collection_name or not collection_name.strip():
        raise ValueError("collection_name não pode ser vazio")

    if len(collection_name) > 255:
        raise ValueError(
            f"collection_name muito longo (máx 255 caracteres). Tamanho: {len(collection_name)}"
        )

    # Qdrant requer nomes alfanuméricos com underscores/hífens
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', collection_name):
        raise ValueError(
            f"collection_name deve conter apenas letras, números, '_' ou '-'. "
            f"Recebido: {collection_name}"
        )

    return collection_name


@resilient(
    max_attempts=3,
    initial_backoff=1.0,
    max_backoff=5.0,
    circuit_breaker=_qdrant_ops_cb,
    retry_on=RETRIABLE_QDRANT_ERRORS
)
def get_or_create_collection(
    collection_name: str,
    vector_size: int = _DEFAULT_VECTOR_SIZE
) -> str:
    """
    Obtém ou cria uma coleção no Qdrant com validações robustas.

    Args:
        collection_name: Nome da coleção
        vector_size: Dimensão dos vetores (padrão: 1536)

    Returns:
        Nome da coleção (validado)

    Raises:
        ConnectionError: Se o cliente Qdrant não estiver disponível
        ValueError: Se os parâmetros forem inválidos
    """
    # Validações
    collection_name = _validate_collection_name(collection_name)
    vector_size = _validate_vector_size(vector_size)

    client = get_qdrant_client()

    try:
        # Tenta obter a coleção existente
        collection_info = client.get_collection(collection_name=collection_name)

        # Verifica se o vector_size é compatível
        existing_size = collection_info.config.params.vectors.size
        if existing_size != vector_size:
            logger.warning(
                f"Coleção '{collection_name}' existe com vector_size={existing_size}, "
                f"mas foi solicitado vector_size={vector_size}. Usando existente."
            )

        logger.info(
            f"Coleção '{collection_name}' já existe "
            f"(vectors={existing_size}, points={collection_info.points_count})."
        )

    except Exception as e:
        # Coleção não existe ou erro ao buscar
        error_msg = str(e).lower()

        if "not found" in error_msg or "doesn't exist" in error_msg:
            logger.warning(
                f"Coleção '{collection_name}' não encontrada. Criando nova coleção "
                f"com vector_size={vector_size}..."
            )

            try:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    ),
                )
                logger.info(f"Coleção '{collection_name}' criada com sucesso.")

            except Exception as create_error:
                logger.error(
                    f"Falha ao criar coleção '{collection_name}': {create_error}",
                    exc_info=True
                )
                raise ConnectionError(
                    f"Não foi possível criar a coleção '{collection_name}': {create_error}"
                ) from create_error

        else:
            # Erro inesperado ao verificar coleção
            logger.error(
                f"Erro inesperado ao verificar coleção '{collection_name}': {e}",
                exc_info=True
            )
            raise

    return collection_name


@resilient(
    max_attempts=5,
    initial_backoff=2.0,
    max_backoff=10.0,
    circuit_breaker=_qdrant_init_cb,
    retry_on=RETRIABLE_QDRANT_ERRORS
)
def check_qdrant_readiness() -> bool:
    """
    Verifica a prontidão do Qdrant com retries e circuit breaker.

    Returns:
        True se o Qdrant estiver pronto

    Raises:
        ConnectionError: Se o Qdrant não estiver acessível após retries
    """
    start = time.perf_counter()

    try:
        client = get_qdrant_client()

        # Operação leve para verificar conectividade
        collections = client.get_collections()

        elapsed = time.perf_counter() - start
        logger.info(
            f"Qdrant readiness check PASSED em {elapsed:.2f}s. "
            f"Coleções disponíveis: {len(collections.collections)}"
        )

        return True

    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.error(
            f"Qdrant readiness check FAILED após {elapsed:.2f}s: {e}",
            exc_info=True
        )
        raise ConnectionError(f"Qdrant não está pronto: {e}") from e


def reset_client():
    """
    Reseta o cliente Qdrant (útil para testes ou reconexões).

    Cuidado: Esta função deve ser usada apenas em situações específicas
    como testes ou após detectar falha de conexão persistente.
    """
    global _qdrant_client, _client_initialized, _init_error

    if _qdrant_client:
        try:
            _qdrant_client.close()
        except Exception as e:
            logger.warning(f"Erro ao fechar cliente Qdrant: {e}")

    _qdrant_client = None
    _client_initialized = False
    _init_error = None

    logger.info("Cliente Qdrant resetado. Próxima chamada irá reinicializar.")


def get_collection_info(collection_name: str) -> dict:
    """
    Obtém informações sobre uma coleção.

    Args:
        collection_name: Nome da coleção

    Returns:
        Dicionário com informações da coleção

    Raises:
        ConnectionError: Se o cliente não estiver disponível
        ValueError: Se o nome da coleção for inválido
    """
    collection_name = _validate_collection_name(collection_name)
    client = get_qdrant_client()

    try:
        info = client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "vector_size": info.config.params.vectors.size,
            "points_count": info.points_count,
            "status": info.status.value if hasattr(info.status, 'value') else str(info.status),
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações da coleção '{collection_name}': {e}")
        raise


# Inicialização eager opcional (comentada por padrão para evitar crashes no import)
# Descomente se desejar tentar conexão na importação do módulo
# try:
#     _lazy_init_client()
# except Exception as e:
#     logger.warning(f"Inicialização eager do Qdrant falhou: {e}")
