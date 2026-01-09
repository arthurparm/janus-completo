import time

import structlog

try:
    from prometheus_client import Counter, Histogram
except Exception:

    class _Noop:
        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

    Histogram = Counter = _Noop
import asyncio
from typing import Any  # Added Optional
from uuid import uuid4

from fastapi import Request
from qdrant_client import models

from app.config import settings
from app.core.embeddings.embedding_manager import embed_text
from app.core.protocols import MemoryRepositoryProtocol
from app.db.vector_store import get_or_create_collection, get_qdrant_client
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)
_MEMORY_SERVICE_LATENCY = Histogram(
    "memory_service_latency_seconds", "Latência por operação do serviço de memória", ["operation"]
)
_MEMORY_SERVICE_ERRORS = Counter(
    "memory_service_errors_total", "Erros no serviço de memória", ["operation", "exception"]
)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""

    pass


class MemoryService:
    """
    Camada de serviço para operações relacionadas à memória episódica.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """

    def __init__(self, repo: MemoryRepositoryProtocol):
        self._repo = repo

    async def add_experience(self, type: str, content: str, metadata: dict[str, Any]) -> Experience:
        """
        Cria uma nova experiência e a delega para o repositório salvar.
        """
        logger.info("Criando e salvando nova experiência via serviço", type=type)
        start = time.perf_counter()
        try:
            experience = Experience(type=type, content=content, metadata=metadata)
            await self._repo.save_experience(experience)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("add_experience").observe(elapsed)
            return experience
        except Exception as e:
            logger.error("Erro no serviço de memória ao adicionar experiência", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("add_experience", type(e).__name__).inc()
            raise MemoryServiceError("Falha ao adicionar experiência.") from e

    async def recall_experiences(
        self, query: str, limit: int | None = None, min_score: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Delega a busca por experiências para o repositório.
        """
        logger.info(
            "Buscando experiências via serviço", query=query, limit=limit, min_score=min_score
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_experiences(
                query=query, limit=limit, min_score=min_score
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_experiences").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço de memória ao buscar experiências", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_experiences", type(e).__name__).inc()
            raise MemoryServiceError("Falha ao buscar experiências.") from e

    async def recall_filtered(
        self,
        query: str | None,
        filters: dict[str, Any],
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        logger.info(
            "Buscando experiências filtradas",
            query=query,
            filters=filters,
            limit=limit,
            min_score=min_score,
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_filtered(
                query=query, filters=filters, limit=limit, min_score=min_score
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_filtered").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar filtrado", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_filtered", type(e).__name__).inc()
            raise MemoryServiceError("Falha na busca filtrada.") from e

    async def recall_by_timeframe(
        self,
        query: str | None,
        start_ts_ms: int | None,
        end_ts_ms: int | None,
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        logger.info(
            "Buscando por janela temporal",
            query=query,
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            limit=limit,
            min_score=min_score,
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_by_timeframe(
                query=query,
                start_ts_ms=start_ts_ms,
                end_ts_ms=end_ts_ms,
                limit=limit,
                min_score=min_score,
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_by_timeframe").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar por janela temporal", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_by_timeframe", type(e).__name__).inc()
            raise MemoryServiceError("Falha na busca por janela temporal.") from e

    async def recall_recent_failures(
        self,
        limit: int | None = 10,
        timeframe_seconds: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        logger.debug(
            "Service: recall_recent_failures",
            limit=limit,
            timeframe_seconds=timeframe_seconds,
            min_score=min_score,
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_recent_failures(
                limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_recent_failures").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar falhas recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_failures", type(e).__name__).inc()
            raise MemoryServiceError(f"Erro ao buscar falhas recentes: {e}")

    async def recall_recent_lessons(
        self,
        limit: int | None = 10,
        timeframe_seconds: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        logger.debug(
            "Service: recall_recent_lessons",
            limit=limit,
            timeframe_seconds=timeframe_seconds,
            min_score=min_score,
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_recent_lessons(
                limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_recent_lessons").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar lições recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_lessons", type(e).__name__).inc()
            raise MemoryServiceError(f"Erro ao buscar lições recentes: {e}")

    async def index_interaction(
        self, content: str, user_id: str, session_id: str, role: str
    ) -> None:
        """
        Indexa uma interação de chat (mensagem do usuário ou assistente) no banco vetorial.
        Executa operações bloqueantes (embedding, IO) em thread separada.
        """
        if not content or not user_id:
            return

        logger.info("Indexando interação no vetor (Memória)", user_id=user_id, role=role)

        def _sync_index_logic():
            try:
                collection_name = get_or_create_collection(f"user_{user_id}")
                client = get_qdrant_client()

                max_points = int(
                    getattr(settings, "CHAT_INDEX_MAX_POINTS_PER_USER", 200000) or 200000
                )

                qfilter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.type", match=models.MatchValue(value="chat_msg")
                        ),
                        models.FieldCondition(
                            key="metadata.user_id", match=models.MatchValue(value=str(user_id))
                        ),
                    ]
                )

                # Check count
                cnt = client.count(
                    collection_name=collection_name, count_filter=qfilter, exact=True
                )
                current = int(getattr(cnt, "count", 0) or 0)

                if current >= max_points:
                    logger.warning("Limite de indexação de chat atingido", user_id=user_id)
                    return

                # Embed and Upsert
                vec = embed_text(content)
                now_ms = int(time.time() * 1000)

                payload = {
                    "content": content,
                    "ts_ms": now_ms,
                    "metadata": {
                        "type": "chat_msg",
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": role,
                        "timestamp": now_ms,
                    },
                }

                # Qdrant requires UUID or int as ID. We store the composite ID in metadata for reference.
                composite_id = f"chat:{user_id}:{session_id}:{uuid4().hex}"
                payload["composite_id"] = composite_id

                # Use a proper UUID for the point ID
                point_id = str(uuid4())
                point = models.PointStruct(id=point_id, vector=vec, payload=payload)

                client.upsert(collection_name=collection_name, points=[point])

            except Exception as e:
                logger.error("Erro ao indexar interação", exc_info=e)
                # Suppress error to avoid breaking chat flow

        # Run in thread pool to avoid blocking async event loop
        await asyncio.to_thread(_sync_index_logic)


# Padrão de Injeção de Dependência: Getter para o serviço
def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service
