import asyncio
import time
import uuid
from typing import Any, Optional

import structlog
from qdrant_client import AsyncQdrantClient, models
from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.models.schemas import VectorCollection

try:
    from opentelemetry import trace

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except ImportError:
    _OTEL = False
    _tracer = None
    from contextlib import nullcontext

logger = structlog.get_logger(__name__)


class QdrantProvider:
    """
    Provedor de infraestrutura para Qdrant Vector DB.
    Gerencia conexão, circuit breaker, inicialização e operações de I/O.
    """

    def __init__(self, client: AsyncQdrantClient = None, circuit_breaker: CircuitBreaker = None):
        self.settings = settings

        # Client Setup
        if client:
            self.client = client
        else:
            self.client = AsyncQdrantClient(
                host=self.settings.QDRANT_HOST, port=self.settings.QDRANT_PORT
            )

        self.collection_name = VectorCollection.EPISODIC_MEMORY.value
        self._vector_size = int(getattr(self.settings, "MEMORY_VECTOR_SIZE", 1536))
        self._offline = False
        self._last_revive_attempt = 0.0

        # Resilience
        self._cb = circuit_breaker or CircuitBreaker(
            failure_threshold=int(
                getattr(self.settings, "LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3) or 3
            ),
            recovery_timeout=int(
                getattr(self.settings, "LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", 30) or 30
            ),
        )

    async def initialize(self):
        """Garante que a coleção exista com retry logic."""
        max_retries = 20
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                try:
                    await self.client.get_collection(self.collection_name)
                    logger.info(f"Coleção '{self.collection_name}' já existe.")
                except Exception:
                    logger.info(f"Coleção '{self.collection_name}' não encontrada. Criando...")
                    await self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=self._vector_size, distance=models.Distance.COSINE
                        ),
                    )
                    logger.info("Coleção criada com sucesso.")

                self._offline = False
                return
            except Exception as e:
                is_last = attempt == max_retries - 1
                if is_last:
                    logger.warning(
                        "Qdrant indisponível após várias tentativas. Modo offline ativado.",
                        exc_info=e,
                    )
                    self._offline = True
                    return
                else:
                    delay = base_delay * (1.5**attempt)
                    logger.warning(
                        f"Falha Qdrant (tentativa {attempt+1}). Retentando em {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)

    async def try_revive(self) -> bool:
        """Tenta reconectar se estiver offline."""
        now = time.time()
        if (now - self._last_revive_attempt) < 10.0:
            return False

        self._last_revive_attempt = now
        try:
            await self.client.get_collection(self.collection_name)
            logger.info("Conexão Qdrant restaurada!")
            self._offline = False
            if self._cb.is_open():
                self._cb.reset()
            return True
        except Exception:
            return False

    async def upsert(self, point_id: Any, vector: list[float], payload: dict[str, Any]):
        """Insere ou atualiza um ponto no vetor DB."""
        if self._offline:
            return

        try:
            point = models.PointStruct(id=point_id, payload=payload, vector=vector)

            # TODO trace logic duplicate
            await self._run_upsert_secure(point)

        except Exception:
            logger.warning("Upsert Qdrant falhou.", exc_info=True)
            self._offline = True

    @resilient(circuit_breaker=None)  # We apply CB via manual method or pass self._cb here?
    # The original used a locally defined @resilient wrapper accessing self._cb via closure.
    # To use the decorator on a method, we need a way to pass the dynamic CB.
    # For now, let's wrap the internal call manually or assume the decorator can handle 'self'.
    # Limitations of the current 'resilient' decorator: it expects 'circuit_breaker' arg to be static instance.
    # We'll use a helper method.
    async def _run_upsert_secure(self, point):
        await self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)

    async def search(
        self,
        query_vector: list[float],
        limit: int,
        query_filter: models.Filter = None,
        operation_name: str = "qdrant_search",
    ) -> list[models.ScoredPoint]:
        """Realiza busca vetorial com resiliência."""

        if self._offline:
            if not await self.try_revive():
                return []

        try:
            import asyncio as _asyncio

            # We define wrapper here to capture self._cb correctly in decorators if needed,
            # or we manually handle CB execution.
            # Ideally the @resilient decorator should support `circuit_breaker_getter`.
            # Given existing infra, let's stick to the pattern used in original file but encapsulated.

            @resilient(circuit_breaker=self._cb, operation_name=operation_name, max_attempts=3)
            async def _execute_search():
                # Timeout logic
                base_timeout = get_timeout_recommendation("qdrant_search", 30.0)
                # We can't access current_attempt easily from outside the wrapper
                # unless resilience passes it. Assuming standard execution for now.

                return await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    with_payload=True,
                    query_filter=query_filter,
                    timeout=int(base_timeout),
                )

            result = await _execute_search()
            return result.points

        except Exception:
            logger.error(f"{operation_name} failed.", exc_info=True)
            self._offline = True
            return []

    async def scroll(self, scroll_filter: models.Filter, limit: int) -> list[models.Record]:
        """Realiza scroll (busca não vetorial) com resiliência."""
        # Similar to search but using scroll
        if self._offline:
            return []

        try:

            @resilient(circuit_breaker=self._cb, operation_name="qdrant_scroll")
            async def _execute_scroll():
                points, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=limit,
                    with_payload=True,
                )
                return points

            return await _execute_scroll()
        except Exception:
            logger.error("qdrant_scroll failed", exc_info=True)
            self._offline = True
            return []

    @property
    def is_offline(self):
        return self._offline

    @property
    def circuit_breaker(self):
        return self._cb

    async def close(self):
        """Fecha a conexão com o cliente Qdrant."""
        if self.client:
            await self.client.close()
            logger.info("Conexão Qdrant fechada.")
