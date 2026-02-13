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
from typing import Any
from uuid import uuid4

from fastapi import Request
from qdrant_client import models

from app.config import settings
from app.core.embeddings.embedding_manager import aembed_text
from app.core.memory.rag_telemetry import confidence_from_scores, emit_step_telemetry
from app.core.protocols import MemoryRepositoryProtocol
from app.db.vector_store import (
    aget_or_create_collection,
    async_count_points,
    get_async_qdrant_client,
)
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)
_MEMORY_SERVICE_LATENCY = Histogram(
    "memory_service_latency_seconds", "LatÃªncia por operaÃ§Ã£o do serviÃ§o de memÃ³ria", ["operation"]
)
_MEMORY_SERVICE_ERRORS = Counter(
    "memory_service_errors_total", "Erros no serviÃ§o de memÃ³ria", ["operation", "exception"]
)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""

    pass


class MemoryService:
    """
    Camada de serviÃ§o para operaÃ§Ãµes relacionadas Ã  memÃ³ria episÃ³dica.
    Orquestra a lÃ³gica de negÃ³cio, recebendo suas dependÃªncias via DI.
    """

    def __init__(self, repo: MemoryRepositoryProtocol):
        self._repo = repo

    def _emit_step_telemetry(
        self,
        *,
        step: str,
        started_at: float,
        confidence: float | None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return emit_step_telemetry(
            endpoint="/memory/service",
            step=step,
            source="memory_service",
            db="qdrant",
            latency_ms=latency_ms,
            confidence=confidence,
            error_code=error_code,
            extra=extra,
        )

    async def add_experience(self, type: str, content: str, metadata: dict[str, Any]) -> Experience:
        """
        Cria uma nova experiÃªncia e a delega para o repositÃ³rio salvar.
        """
        logger.info("Criando e salvando nova experiÃªncia via serviÃ§o", type=type)
        start = time.perf_counter()
        try:
            experience = Experience(type=type, content=content, metadata=metadata)
            await self._repo.save_experience(experience)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("add_experience").observe(elapsed)
            self._emit_step_telemetry(step="add_experience", started_at=start, confidence=1.0, extra={"experience_type": type})
            return experience
        except Exception as e:
            logger.error("Erro no serviÃ§o de memÃ³ria ao adicionar experiÃªncia", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("add_experience", type(e).__name__).inc()
            self._emit_step_telemetry(step="add_experience", started_at=start, confidence=0.0, error_code=type(e).__name__)
            raise MemoryServiceError("Falha ao adicionar experiÃªncia.") from e

    async def recall_experiences(
        self, query: str, limit: int | None = None, min_score: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Delega a busca por experiÃªncias para o repositÃ³rio.
        """
        logger.info(
            "Buscando experiÃªncias via serviÃ§o", query=query, limit=limit, min_score=min_score
        )
        start = time.perf_counter()
        try:
            result = await self._repo.search_experiences(
                query=query, limit=limit, min_score=min_score
            )
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_experiences").observe(elapsed)
            self._emit_step_telemetry(step="recall_experiences", started_at=start, confidence=confidence_from_scores([r.get("score") for r in result if isinstance(r, dict)]), extra={"result_count": len(result)})
            return result
        except Exception as e:
            logger.error("Erro no serviÃ§o de memÃ³ria ao buscar experiÃªncias", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_experiences", type(e).__name__).inc()
            self._emit_step_telemetry(step="recall_experiences", started_at=start, confidence=0.0, error_code=type(e).__name__)
            raise MemoryServiceError("Falha ao buscar experiÃªncias.") from e

    async def recall_filtered(
        self,
        query: str | None,
        filters: dict[str, Any],
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        logger.info(
            "Buscando experiÃªncias filtradas",
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
            self._emit_step_telemetry(step="recall_filtered", started_at=start, confidence=confidence_from_scores([r.get("score") for r in result if isinstance(r, dict)]), extra={"result_count": len(result)})
            return result
        except Exception as e:
            logger.error("Erro no serviÃ§o ao buscar filtrado", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_filtered", type(e).__name__).inc()
            self._emit_step_telemetry(step="recall_filtered", started_at=start, confidence=0.0, error_code=type(e).__name__)
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
            self._emit_step_telemetry(step="recall_by_timeframe", started_at=start, confidence=confidence_from_scores([r.get("score") for r in result if isinstance(r, dict)]), extra={"result_count": len(result)})
            return result
        except Exception as e:
            logger.error("Erro no serviÃ§o ao buscar por janela temporal", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_by_timeframe", type(e).__name__).inc()
            self._emit_step_telemetry(step="recall_by_timeframe", started_at=start, confidence=0.0, error_code=type(e).__name__)
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
            self._emit_step_telemetry(step="recall_recent_failures", started_at=start, confidence=confidence_from_scores([r.get("score") for r in result if isinstance(r, dict)]), extra={"result_count": len(result)})
            return result
        except Exception as e:
            logger.error("Erro no serviÃ§o ao buscar falhas recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_failures", type(e).__name__).inc()
            self._emit_step_telemetry(step="recall_recent_failures", started_at=start, confidence=0.0, error_code=type(e).__name__)
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
            self._emit_step_telemetry(step="recall_recent_lessons", started_at=start, confidence=confidence_from_scores([r.get("score") for r in result if isinstance(r, dict)]), extra={"result_count": len(result)})
            return result
        except Exception as e:
            logger.error("Erro no serviÃ§o ao buscar liÃ§Ãµes recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_lessons", type(e).__name__).inc()
            self._emit_step_telemetry(step="recall_recent_lessons", started_at=start, confidence=0.0, error_code=type(e).__name__)
            raise MemoryServiceError(f"Erro ao buscar liÃ§Ãµes recentes: {e}")

    async def index_interaction(
        self, content: str, user_id: str, session_id: str, role: str
    ) -> None:
        """Indexa uma interaÃ§Ã£o de chat (async) no Qdrant."""
        if not content or not user_id:
            return

        logger.info("Indexando interaÃ§Ã£o no vetor (MemÃ³ria)", user_id=user_id, role=role)
        try:
            collection_name = await aget_or_create_collection(f"user_{user_id}")
            client = get_async_qdrant_client()

            max_points = int(getattr(settings, "CHAT_INDEX_MAX_POINTS_PER_USER", 200000) or 200000)

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

            current = await async_count_points(client, collection_name, qfilter, exact=True)
            if current >= max_points:
                logger.warning("Limite de indexaÃ§Ã£o de chat atingido", user_id=user_id)
                return

            vec = await aembed_text(content)
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

            composite_id = f"chat:{user_id}:{session_id}:{uuid4().hex}"
            payload["composite_id"] = composite_id
            point_id = str(uuid4())
            point = models.PointStruct(id=point_id, vector=vec, payload=payload)

            await client.upsert(collection_name=collection_name, points=[point])

        except Exception:
            logger.warning("Falha ao indexar interaÃ§Ã£o", exc_info=True)


# PadrÃ£o de InjeÃ§Ã£o de DependÃªncia: Getter para o serviÃ§o
def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service


