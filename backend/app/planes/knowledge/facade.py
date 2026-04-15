from __future__ import annotations

import time
from typing import Any, cast

import structlog

from app.config import settings
from app.services.document_service import DocumentIngestionService
from app.services.knowledge_service import KnowledgeService
from app.services.memory_service import MemoryService
from app.services.rag_service import RAGService

from .adapters import (
    ExperimentalQuantizedRetrievalAdapter,
    GraphKnowledgeAdapter,
    QdrantKnowledgeAdapter,
)
from .contracts import RetrievalBackendDecision, RetrievalBackendName
from .experimental_index import (
    ExperimentalBuildResult,
    ExperimentalDomain,
    ExperimentalIndexManager,
    compare_result_sets,
)

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter as _PrometheusCounter
    from prometheus_client import Histogram as _PrometheusHistogram
except Exception:

    class _MetricNoop:
        def labels(self, *args: Any, **kwargs: Any) -> "_MetricNoop":
            del args, kwargs
            return self

        def inc(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs
            pass

        def observe(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs
            pass

    _PrometheusCounter = _MetricNoop
    _PrometheusHistogram = _MetricNoop


_KNOWLEDGE_RETRIEVAL_REQUESTS = _PrometheusCounter(
    "knowledge_retrieval_requests_total",
    "Knowledge retrieval requests by backend/outcome",
    ["backend", "operation", "outcome"],
)
_KNOWLEDGE_RETRIEVAL_LATENCY = _PrometheusHistogram(
    "knowledge_retrieval_latency_seconds",
    "Knowledge retrieval latency by backend/operation",
    ["backend", "operation"],
)
_KNOWLEDGE_RETRIEVAL_RESULTS = _PrometheusHistogram(
    "knowledge_retrieval_result_count",
    "Knowledge retrieval result count by backend/operation",
    ["backend", "operation"],
)
_KNOWLEDGE_RETRIEVAL_AVG_SCORE = _PrometheusHistogram(
    "knowledge_retrieval_avg_score",
    "Knowledge retrieval average score by backend/operation",
    ["backend", "operation"],
)
_KNOWLEDGE_RETRIEVAL_COVERAGE = _PrometheusHistogram(
    "knowledge_retrieval_citation_coverage",
    "Knowledge retrieval citation coverage proxy by backend/operation",
    ["backend", "operation"],
)
_KNOWLEDGE_RETRIEVAL_COMPARE_DIFF = _PrometheusHistogram(
    "knowledge_retrieval_compare_diff",
    "Knowledge retrieval overlap diff between active and shadow backends",
    ["active_backend", "shadow_backend", "operation"],
)
_KNOWLEDGE_RETRIEVAL_FALLBACKS = _PrometheusCounter(
    "knowledge_retrieval_fallback_total",
    "Knowledge retrieval fallback/shadow failures",
    ["backend", "operation", "reason"],
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
        experimental_adapter: ExperimentalQuantizedRetrievalAdapter | None = None,
        experimental_index_manager: ExperimentalIndexManager | None = None,
    ):
        self._memory_service = memory_service
        self._knowledge_service = knowledge_service
        self._document_service = document_service
        self._rag_service = rag_service
        self._qdrant = qdrant_adapter or QdrantKnowledgeAdapter()
        self._graph = graph_adapter or GraphKnowledgeAdapter()
        self._experimental_index_manager = experimental_index_manager or ExperimentalIndexManager()
        self._experimental = experimental_adapter or ExperimentalQuantizedRetrievalAdapter(
            index_manager=self._experimental_index_manager
        )

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
        last_build = self._experimental_index_manager.last_build_summary()
        return {
            "active_backend": decision.active_backend.value,
            "shadow_backend": decision.shadow_backend.value if decision.shadow_backend else None,
            "experimental_collection_suffix": getattr(
                settings, "KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX", None
            ),
            "experimental_index_enabled": bool(
                getattr(settings, "KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED", False)
            ),
            "experimental_index_version": getattr(
                settings, "KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION", "v1"
            ),
            "experimental_write_dual": bool(
                getattr(settings, "KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL", False)
            ),
            "compare_on_read": bool(getattr(settings, "KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ", False)),
            "promotion_allowed": bool(
                getattr(settings, "KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED", False)
            ),
            "last_build": last_build,
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
        return cast(
            list[dict[str, Any]],
            await self._rag_service.retrieve_context(
            message=message,
            conversation_id=conversation_id,
            limit=limit,
            caller_endpoint=caller_endpoint,
            ),
        )

    async def search_memories(
        self, *, query: str, filters: dict[str, Any], limit: int | None = None, min_score: float | None = None
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            await self._memory_service.recall_filtered(
                query=query, filters=filters, limit=limit, min_score=min_score
            ),
        )

    async def index_chat_message(self, *, content: str, session_id: str, role: str) -> None:
        await self._memory_service.index_interaction(content=content, session_id=session_id, role=role)

    async def index_document(self, **kwargs: Any) -> dict[str, Any]:
        result = cast(dict[str, Any], await self._document_service.ingest_file(**kwargs))
        if bool(getattr(settings, "KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL", False)) and result.get("doc_id"):
            try:
                await self.build_experimental_index(
                    domain="docs",
                    rebuild_full=True,
                    dry_run=False,
                )
            except Exception as exc:
                logger.warning("experimental_doc_dual_write_failed", error=str(exc))
                _KNOWLEDGE_RETRIEVAL_FALLBACKS.labels(
                    RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL.value,
                    "index_document",
                    "dual_write_error",
                ).inc()
        return result

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
        return cast(
            list[dict[str, Any]],
            await self._execute_active_search(
            operation="search_documents",
            execute=lambda backend: backend.search_documents(
                query=query,
                user_id=user_id,
                doc_id=doc_id,
                knowledge_space_id=knowledge_space_id,
                limit=limit,
                min_score=min_score,
                collection_suffix=getattr(settings, "KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX", None)
                if backend is self._qdrant
                and self.retrieval_backend_decision().active_backend
                == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL
                else None,
            ),
            active_backend_name=self.retrieval_backend_decision().active_backend,
            ),
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
        return cast(
            list[Any],
            await self._execute_active_search(
            operation="search_user_chat",
            execute=lambda backend: backend.search_user_chat(
                query=query,
                user_id=user_id,
                session_id=session_id,
                role=role,
                limit=limit,
                min_score=min_score,
                start_ts=start_ts,
                end_ts=end_ts,
                exclude_duplicate=exclude_duplicate,
            ),
            active_backend_name=self.retrieval_backend_decision().active_backend,
            ),
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
        return cast(
            list[Any],
            await self._execute_active_search(
            operation="search_user_memory",
            execute=lambda backend: backend.search_user_memory(
                query=query,
                user_id=user_id,
                limit=limit,
                min_score=min_score,
                memory_type=memory_type,
                origin=origin,
                exclude_duplicate=exclude_duplicate,
            ),
            active_backend_name=self.retrieval_backend_decision().active_backend,
            ),
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
        if bool(getattr(settings, "KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL", False)):
            try:
                await self._experimental.index_memory_event(
                    user_id=user_id,
                    content=content,
                    point_id=point_id,
                    payload=payload,
                )
            except Exception as exc:
                logger.warning("experimental_memory_dual_write_failed", error=str(exc))
                _KNOWLEDGE_RETRIEVAL_FALLBACKS.labels(
                    RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL.value,
                    "index_memory_event",
                    "dual_write_error",
                ).inc()

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

    async def build_experimental_index(
        self,
        *,
        domain: ExperimentalDomain,
        user_id: str | None = None,
        knowledge_space_id: str | None = None,
        doc_id: str | None = None,
        rebuild_full: bool = False,
        since_ts: int | None = None,
        dry_run: bool = False,
    ) -> ExperimentalBuildResult:
        return await self._experimental_index_manager.build_index(
            domain=domain,
            user_id=user_id,
            knowledge_space_id=knowledge_space_id,
            doc_id=doc_id,
            rebuild_full=rebuild_full,
            since_ts=since_ts,
            dry_run=dry_run,
        )

    async def append_experimental_point(
        self,
        *,
        domain: ExperimentalDomain,
        point_id: str,
        vector: list[float] | tuple[float, ...] | Any,
        payload: dict[str, Any],
    ) -> None:
        await self._experimental_index_manager.append_point(
            domain=domain,
            point_id=point_id,
            vector=vector,
            payload=payload,
        )

    async def compare_retrieval(
        self,
        *,
        operation: str,
        query: str,
        user_id: str = "default",
        limit: int = 5,
        min_score: float | None = None,
        session_id: str | None = None,
        role: str | None = None,
        memory_type: str | None = None,
        origin: str | None = None,
        doc_id: str | None = None,
        knowledge_space_id: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        exclude_duplicate: bool = False,
    ) -> dict[str, Any]:
        if operation == "search_documents":
            active = await self._qdrant.search_documents(
                query=query,
                user_id=user_id,
                doc_id=doc_id,
                knowledge_space_id=knowledge_space_id,
                limit=limit,
                min_score=min_score,
            )
            shadow = await self._experimental.search_documents(
                query=query,
                user_id=user_id,
                doc_id=doc_id,
                knowledge_space_id=knowledge_space_id,
                limit=limit,
                min_score=min_score,
            )
            diff = compare_result_sets(
                [self._doc_result_to_point(item) for item in active],
                [self._doc_result_to_point(item) for item in shadow],
            )
            return {"active": active, "shadow": shadow, "compare_diff": diff.__dict__}
        if operation == "search_user_chat":
            active = await self._qdrant.search_user_chat(
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
            shadow = await self._experimental.search_user_chat(
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
            diff = compare_result_sets(active, shadow)
            return {
                "active": [self._point_to_dict(item) for item in active],
                "shadow": [self._point_to_dict(item) for item in shadow],
                "compare_diff": diff.__dict__,
            }
        active = await self._qdrant.search_user_memory(
            query=query,
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            memory_type=memory_type,
            origin=origin,
            exclude_duplicate=exclude_duplicate,
        )
        shadow = await self._experimental.search_user_memory(
            query=query,
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            memory_type=memory_type,
            origin=origin,
            exclude_duplicate=exclude_duplicate,
        )
        diff = compare_result_sets(active, shadow)
        return {
            "active": [self._point_to_dict(item) for item in active],
            "shadow": [self._point_to_dict(item) for item in shadow],
            "compare_diff": diff.__dict__,
        }

    def _active_adapter(self) -> Any:
        decision = self.retrieval_backend_decision()
        if decision.active_backend == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL:
            return self._experimental
        return self._qdrant

    def _shadow_adapter(self) -> tuple[RetrievalBackendName | None, Any | None]:
        decision = self.retrieval_backend_decision()
        if decision.shadow_backend == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL:
            return decision.shadow_backend, self._experimental
        return None, None

    async def _execute_active_search(
        self,
        *,
        operation: str,
        execute: Any,
        active_backend_name: RetrievalBackendName,
    ) -> Any:
        started_at = time.perf_counter()
        backend = self._active_adapter()
        backend_name = active_backend_name.value
        try:
            results = await execute(backend)
            _KNOWLEDGE_RETRIEVAL_REQUESTS.labels(backend_name, operation, "success").inc()
            self._observe_result_metrics(backend_name=backend_name, operation=operation, results=results)
            shadow_backend_name, shadow_adapter = self._shadow_adapter()
            if shadow_adapter is not None and (
                bool(getattr(settings, "KNOWLEDGE_RETRIEVAL_SHADOW_MODE", False))
                or bool(getattr(settings, "KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ", False))
            ):
                await self._run_shadow_compare(
                    operation=operation,
                    execute=execute,
                    active_results=results,
                    shadow_backend_name=shadow_backend_name,
                    shadow_adapter=shadow_adapter,
                    active_backend_name=active_backend_name,
                )
            return results
        except Exception:
            _KNOWLEDGE_RETRIEVAL_REQUESTS.labels(backend_name, operation, "error").inc()
            raise
        finally:
            _KNOWLEDGE_RETRIEVAL_LATENCY.labels(backend_name, operation).observe(
                max(0.0, time.perf_counter() - started_at)
            )

    async def _run_shadow_compare(
        self,
        *,
        operation: str,
        execute: Any,
        active_results: Any,
        shadow_backend_name: RetrievalBackendName | None,
        shadow_adapter: Any,
        active_backend_name: RetrievalBackendName,
    ) -> None:
        if shadow_backend_name is None:
            return
        try:
            shadow_results = await execute(shadow_adapter)
            diff = compare_result_sets(
                self._as_point_list(active_results),
                self._as_point_list(shadow_results),
            )
            _KNOWLEDGE_RETRIEVAL_COMPARE_DIFF.labels(
                active_backend_name.value, shadow_backend_name.value, operation
            ).observe(max(0.0, 1.0 - diff.overlap_ratio))
        except Exception as exc:
            logger.warning("knowledge_shadow_compare_failed", operation=operation, error=str(exc))
            _KNOWLEDGE_RETRIEVAL_FALLBACKS.labels(
                shadow_backend_name.value, operation, "shadow_compare_error"
            ).inc()

    def _observe_result_metrics(self, *, backend_name: str, operation: str, results: Any) -> None:
        result_count = float(len(results or []))
        _KNOWLEDGE_RETRIEVAL_RESULTS.labels(backend_name, operation).observe(result_count)
        if not results:
            _KNOWLEDGE_RETRIEVAL_AVG_SCORE.labels(backend_name, operation).observe(0.0)
            _KNOWLEDGE_RETRIEVAL_COVERAGE.labels(backend_name, operation).observe(0.0)
            return
        scores: list[float] = []
        covered = 0
        for item in results:
            if isinstance(item, dict):
                scores.append(float(item.get("score") or 0.0))
                if item.get("doc_id") or item.get("file_name"):
                    covered += 1
                continue
            scores.append(float(getattr(item, "score", 0.0) or 0.0))
            payload = getattr(item, "payload", None) or {}
            metadata = payload.get("metadata") or {}
            if payload.get("content") or metadata.get("doc_id") or metadata.get("session_id"):
                covered += 1
        avg_score = sum(scores) / max(1, len(scores))
        coverage = covered / max(1, len(results))
        _KNOWLEDGE_RETRIEVAL_AVG_SCORE.labels(backend_name, operation).observe(avg_score)
        _KNOWLEDGE_RETRIEVAL_COVERAGE.labels(backend_name, operation).observe(coverage)

    def _point_to_dict(self, point: Any) -> dict[str, Any]:
        payload = getattr(point, "payload", None) or {}
        return {
            "id": getattr(point, "id", None),
            "score": getattr(point, "score", None),
            "payload": payload,
        }

    def _doc_result_to_point(self, item: dict[str, Any]) -> Any:
        payload = {
            "metadata": {
                "doc_id": item.get("doc_id"),
                "file_name": item.get("file_name"),
                "index": item.get("index"),
                "timestamp": item.get("timestamp"),
                "knowledge_space_id": item.get("knowledge_space_id"),
                "section_title": item.get("section_title"),
            }
        }
        return self._point_to_namespace(item.get("id"), item.get("score"), payload)

    def _point_to_namespace(self, point_id: Any, score: Any, payload: dict[str, Any]) -> Any:
        return type(
            "KnowledgePoint",
            (),
            {"id": point_id, "score": score, "payload": payload},
        )()

    def _as_point_list(self, results: Any) -> list[Any]:
        if not results:
            return []
        if isinstance(results[0], dict):
            return [self._doc_result_to_point(item) for item in results]
        return list(results)
