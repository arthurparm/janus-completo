from __future__ import annotations

import time
from typing import Any

import structlog

from app.config import settings
from app.services.document_service import DocumentIngestionService
from app.services.knowledge_service import KnowledgeService
from app.services.memory_service import MemoryService
from app.services.rag_service import RAGService

from .adapters import GraphKnowledgeAdapter, QdrantKnowledgeAdapter
from .contracts import RetrievalBackendDecision, RetrievalBackendName

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Histogram  # type: ignore
except Exception:

    class Counter:  # type: ignore[override]
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:  # type: ignore[override]
        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass


_KNOWLEDGE_RETRIEVAL_REQUESTS = Counter(
    "knowledge_retrieval_requests_total",
    "Knowledge retrieval requests by backend/outcome",
    ["backend", "operation", "outcome"],
)
_KNOWLEDGE_RETRIEVAL_LATENCY = Histogram(
    "knowledge_retrieval_latency_seconds",
    "Knowledge retrieval latency by backend/operation",
    ["backend", "operation"],
)


class KnowledgeFacade:
    def __init__(
        self,
        *,
        memory_service: MemoryService,
        knowledge_service: KnowledgeService,
        document_service: DocumentIngestionService,
        rag_service: RAGService | None = None,
        qdrant_adapter: QdrantKnowledgeAdapter | None = None,
        graph_adapter: GraphKnowledgeAdapter | None = None,
    ):
        self._memory_service = memory_service
        self._knowledge_service = knowledge_service
        self._document_service = document_service
        self._rag_service = rag_service
        self._qdrant = qdrant_adapter or QdrantKnowledgeAdapter()
        self._graph = graph_adapter or GraphKnowledgeAdapter()

    def retrieval_backend_decision(self) -> RetrievalBackendDecision:
        active_raw = str(
            getattr(settings, "KNOWLEDGE_RETRIEVAL_BACKEND", RetrievalBackendName.BASELINE_QDRANT.value)
        ).strip().lower()
        if active_raw == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL.value:
            active = RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL
        else:
            active = RetrievalBackendName.BASELINE_QDRANT
        shadow = (
            RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL
            if bool(getattr(settings, "KNOWLEDGE_RETRIEVAL_SHADOW_MODE", False))
            and active != RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL
            else None
        )
        return RetrievalBackendDecision(active_backend=active, shadow_backend=shadow)

    def health_snapshot(self) -> dict[str, Any]:
        decision = self.retrieval_backend_decision()
        return {
            "active_backend": decision.active_backend.value,
            "shadow_backend": decision.shadow_backend.value if decision.shadow_backend else None,
            "experimental_collection_suffix": getattr(
                settings, "KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX", None
            ),
        }

    async def retrieve_context(
        self,
        *,
        message: str,
        conversation_id: str | None,
        limit: int = 5,
        caller_endpoint: str = "/chat/rag",
    ) -> list[dict[str, Any]]:
        if self._rag_service is None:
            return []
        return await self._rag_service.retrieve_context(
            message=message,
            conversation_id=conversation_id,
            limit=limit,
            caller_endpoint=caller_endpoint,
        )

    async def search_memories(
        self, *, query: str, filters: dict[str, Any], limit: int | None = None, min_score: float | None = None
    ) -> list[dict[str, Any]]:
        return await self._memory_service.recall_filtered(
            query=query, filters=filters, limit=limit, min_score=min_score
        )

    async def index_chat_message(self, *, content: str, session_id: str, role: str) -> None:
        await self._memory_service.index_interaction(content=content, session_id=session_id, role=role)

    async def index_document(self, **kwargs: Any) -> dict[str, Any]:
        return await self._document_service.ingest_file(**kwargs)

    async def search_documents(
        self,
        *,
        query: str,
        user_id: str,
        doc_id: str | None = None,
        knowledge_space_id: str | None = None,
        limit: int = 5,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        decision = self.retrieval_backend_decision()
        started_at = time.perf_counter()
        backend_name = decision.active_backend.value
        try:
            if decision.active_backend == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL:
                results = await self._qdrant.search_documents(
                    query=query,
                    user_id=user_id,
                    doc_id=doc_id,
                    knowledge_space_id=knowledge_space_id,
                    limit=limit,
                    min_score=min_score,
                    collection_suffix=getattr(settings, "KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX", None),
                )
            else:
                results = await self._qdrant.search_documents(
                    query=query,
                    user_id=user_id,
                    doc_id=doc_id,
                    knowledge_space_id=knowledge_space_id,
                    limit=limit,
                    min_score=min_score,
                )
            _KNOWLEDGE_RETRIEVAL_REQUESTS.labels(backend_name, "search_documents", "success").inc()
            return results
        except Exception:
            _KNOWLEDGE_RETRIEVAL_REQUESTS.labels(backend_name, "search_documents", "error").inc()
            raise
        finally:
            _KNOWLEDGE_RETRIEVAL_LATENCY.labels(backend_name, "search_documents").observe(
                max(0.0, time.perf_counter() - started_at)
            )

    async def delete_document(self, *, doc_id: str, user_id: str) -> None:
        await self._qdrant.delete_document(doc_id=doc_id, user_id=user_id)

    async def get_document_points(self, *, doc_id: str, user_id: str, limit: int = 10) -> tuple[list[Any], int]:
        return await self._qdrant.get_document_points(doc_id=doc_id, user_id=user_id, limit=limit)

    async def search_user_chat(
        self,
        *,
        query: str,
        user_id: str,
        session_id: str | None,
        role: str | None,
        limit: int,
        min_score: float | None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        exclude_duplicate: bool = False,
    ) -> list[Any]:
        return await self._qdrant.search_user_chat(
            query=query,
            user_id=user_id,
            session_id=session_id,
            role=role,
            limit=limit,
            min_score=min_score,
            start_ts=start_ts,
            end_ts=end_ts,
            exclude_duplicate=exclude_duplicate,
        )

    async def search_user_memory(
        self,
        *,
        query: str,
        user_id: str,
        limit: int,
        min_score: float | None,
        memory_type: str | None = None,
        origin: str | None = None,
        exclude_duplicate: bool = False,
    ) -> list[Any]:
        return await self._qdrant.search_user_memory(
            query=query,
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            memory_type=memory_type,
            origin=origin,
            exclude_duplicate=exclude_duplicate,
        )

    async def index_memory_event(
        self,
        *,
        user_id: str,
        content: str,
        point_id: str,
        payload: dict[str, Any],
    ) -> None:
        await self._qdrant.index_memory_event(
            user_id=user_id, content=content, point_id=point_id, payload=payload
        )

    async def load_user_timeline_points(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        query: str | None,
        start_ts: int | None,
        end_ts: int | None,
        limit: int,
    ) -> list[Any]:
        return await self._qdrant.load_user_timeline_points(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
        )
