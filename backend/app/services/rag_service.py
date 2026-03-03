import asyncio
import time
from typing import Any, Optional

import structlog

from qdrant_client import models as qdrant_models

from app.config import settings
from app.core.embeddings.embedding_manager import aembed_text
from app.core.llm import ModelPriority, ModelRole
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.memory.rag_telemetry import confidence_from_scores, emit_step_telemetry
from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client
from app.repositories.chat_repository import ChatRepository
from app.services.semantic_reranker_service import get_semantic_reranker
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.user_preference_memory_service import user_preference_memory_service

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Histogram
except Exception:

    class _Noop:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    Counter = Histogram = _Noop

_RAG_LATENCY = Histogram(
    "rag_service_latency_seconds", "Latency per RAG service operation", ["operation"]
)
_RAG_ERRORS = Counter(
    "rag_service_errors_total", "Errors in RAG service", ["operation", "exception"]
)
_RAG_OPS = Counter(
    "rag_service_operations_total", "Operations in RAG service", ["operation", "outcome"]
)
_RAG_SKIPPED = Counter(
    "rag_service_skipped_total", "Skipped RAG service operations", ["operation", "reason"]
)
_RAG_RESULTS = Counter(
    "rag_service_results_total", "RAG result items", ["operation"]
)


# --- Custom Exceptions ---
class RAGServiceError(Exception):
    """Base exception for RAG service errors."""

    pass


class RAGService:
    """
    Service responsible for Retrieval-Augmented Generation (RAG) operations,
    including memory retrieval, indexing, and conversation summarization.
    """

    def __init__(
        self,
        repo: ChatRepository,
        llm_service: LLMService,
        memory_service: Optional[MemoryService] = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._memory = memory_service
        self._reranker = get_semantic_reranker()

    def _format_memories(self, memories: list[dict[str, Any]]) -> Optional[str]:
        memory_lines = []
        for m in memories:
            content = ""
            mem_type = "memory"
            if isinstance(m, dict):
                content = (
                    m.get("content", "")
                    or (m.get("payload") or {}).get("content", "")
                    or m.get("page_content", "")
                )
                mem_type = (
                    m.get("type")
                    or (m.get("metadata") or {}).get("type")
                    or "memory"
                )
            else:
                content = getattr(m, "content", "") or ""
                mem_type = getattr(m, "type", "memory")

            if not content:
                continue
            content_preview = content[:500] + "..." if len(content) > 500 else content
            memory_lines.append(f"- [{mem_type}]: {content_preview}")

        return "\n".join(memory_lines) if memory_lines else None

    def _emit_step_telemetry(
        self,
        *,
        endpoint: str,
        step: str,
        started_at: float,
        db: str,
        confidence: float | None,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        emit_step_telemetry(
            endpoint=endpoint,
            step=step,
            source="rag_service",
            db=db,
            latency_ms=(time.perf_counter() - started_at) * 1000,
            confidence=confidence,
            error_code=error_code,
            extra=extra,
        )

    async def retrieve_context(
        self,
        message: str,
        limit: int = 5,
        user_id: str | None = None,
        conversation_id: str | None = None,
        caller_endpoint: str = "/chat/rag",
        transport: str = "unknown",
        identity_source: str = "unknown",
    ) -> Optional[str]:
        """Retrieves relevant memories for the current message."""
        start = time.perf_counter()
        telemetry_base = {
            "transport": transport,
            "identity_source": identity_source,
            "user_id_present": bool(user_id),
            "conversation_id_present": bool(conversation_id),
        }
        if not self._memory:
            _RAG_SKIPPED.labels("retrieve_context", "no_memory_service").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_NO_MEMORY_SERVICE",
                extra=telemetry_base,
            )
            return None
        if not message:
            _RAG_SKIPPED.labels("retrieve_context", "empty_message").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_EMPTY_MESSAGE",
                extra=telemetry_base,
            )
            return None
        if not user_id:
            logger.debug("RAG context skipped: missing user_id")
            _RAG_SKIPPED.labels("retrieve_context", "missing_user_id").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_MISSING_USER_ID",
                extra=telemetry_base,
            )
            return None

        try:
            try:
                await user_preference_memory_service.maybe_capture_from_message(
                    message=message,
                    user_id=str(user_id),
                    conversation_id=conversation_id,
                )
            except Exception as pref_exc:
                logger.warning("user_preference_capture_failed_in_rag", error=str(pref_exc))

            vec = await aembed_text(message)
            collection_name = await aget_or_create_collection(f"user_{user_id}")
            client = get_async_qdrant_client()
            candidate_multiplier = max(1, int(getattr(settings, "RAG_RERANK_CANDIDATE_MULTIPLIER", 3)))
            query_limit = (
                max(int(limit), int(limit) * candidate_multiplier)
                if bool(getattr(settings, "RAG_RERANK_ENABLED", True))
                else int(limit)
            )

            must: list[qdrant_models.FieldCondition] = [
                qdrant_models.FieldCondition(
                    key="metadata.user_id",
                    match=qdrant_models.MatchValue(value=str(user_id)),
                )
            ]
            # Não filtrar por session_id para permitir recuperar documentos/chunks globais do usuário
            # (documentos ingeridos não têm session_id).

            qfilter = qdrant_models.Filter(must=must)
            res = await client.query_points(
                collection_name=collection_name,
                query=vec,
                limit=query_limit,
                with_payload=True,
                query_filter=qfilter,
            )
            hits = getattr(res, "points", res) or []

            memories: list[dict[str, Any]] = []
            for h in hits:
                score = getattr(h, "score", None)
                payload = getattr(h, "payload", {}) or {}
                meta = payload.get("metadata") or {}
                memories.append(
                    {
                        "content": payload.get("content", ""),
                        "metadata": meta,
                        "type": meta.get("type", "memory"),
                        "score": score,
                    }
                )
            preference_items: list[dict[str, Any]] = []
            try:
                preference_items = await user_preference_memory_service.list_preferences(
                    user_id=str(user_id),
                    query=message,
                    limit=min(5, max(1, limit)),
                    active_only=True,
                )
            except Exception as pref_exc:
                logger.warning("user_preference_retrieve_failed_in_rag", error=str(pref_exc))

            rerank_applied = False
            rerank_method = "none"
            rerank_candidate_count = len(memories)
            if memories:
                rerank_result = await self._reranker.rerank(query=message, items=memories, top_k=limit)
                memories = rerank_result.items
                rerank_applied = rerank_result.applied
                rerank_method = rerank_result.method
                rerank_candidate_count = int(rerank_result.candidate_count)
            memories = [
                item for item in memories
                if str((item.get("metadata") or {}).get("type") or "").lower() != "user_preference"
            ]
            preference_context = user_preference_memory_service.format_preference_context(preference_items)
            generic_context = self._format_memories(memories)
            combined_context = self._combine_memory_context(preference_context, generic_context)

            _RAG_OPS.labels("retrieve_context", "success").inc()
            scores = [m.get("score") for m in memories]
            if combined_context:
                _RAG_RESULTS.labels("retrieve_context").inc(len(memories))
                logger.info("RAG enrichment: retrieved %d relevant memories", len(memories))
                _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
                self._emit_step_telemetry(
                    endpoint=caller_endpoint,
                    step="retrieve_context",
                    started_at=start,
                    db="qdrant",
                    confidence=confidence_from_scores(scores),
                    extra={
                        **telemetry_base,
                        "result_count": len(memories),
                        "limit": int(limit),
                        "query_limit": int(query_limit),
                        "rerank_applied": rerank_applied,
                        "rerank_method": rerank_method,
                        "rerank_candidate_count": int(rerank_candidate_count),
                        "rerank_top_k": int(limit),
                        "user_preferences_count": len(preference_items),
                    },
                )
                return combined_context

            _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                extra={
                    **telemetry_base,
                    "result_count": 0,
                    "limit": int(limit),
                    "query_limit": int(query_limit),
                    "rerank_applied": False,
                    "rerank_method": "none",
                    "rerank_candidate_count": int(rerank_candidate_count),
                    "rerank_top_k": int(limit),
                    "user_preferences_count": len(preference_items),
                },
            )
            return None
        except Exception as e:
            _RAG_OPS.labels("retrieve_context", "error").inc()
            _RAG_ERRORS.labels("retrieve_context", type(e).__name__).inc()
            _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code=type(e).__name__,
                extra={**telemetry_base, "limit": int(limit)},
            )
            logger.warning("Failed to retrieve memories for prompt enrichment", error=str(e))
            # We don't raise here to prevent blocking the chat response if memory fails
            return None

    def _combine_memory_context(
        self, preference_context: str | None, generic_context: str | None
    ) -> str | None:
        if preference_context and generic_context:
            return f"{preference_context}\n\n{generic_context}"
        return preference_context or generic_context

    async def maybe_index_message(
        self,
        text: str,
        user_id: Optional[str],
        conversation_id: str,
        role: str,
        caller_endpoint: str = "/chat/rag",
        transport: str = "unknown",
        identity_source: str = "unknown",
    ) -> None:
        start = time.perf_counter()
        telemetry_base = {
            "transport": transport,
            "identity_source": identity_source,
            "user_id_present": bool(user_id),
            "conversation_id_present": bool(conversation_id),
        }
        if not text:
            _RAG_SKIPPED.labels("index_message", "empty_text").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="index_message",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_EMPTY_TEXT",
                extra=telemetry_base,
            )
            return
        if not user_id:
            _RAG_SKIPPED.labels("index_message", "missing_user_id").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="index_message",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_MISSING_USER_ID",
                extra=telemetry_base,
            )
            return
        if not self._memory:
            _RAG_SKIPPED.labels("index_message", "no_memory_service").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="index_message",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code="SKIPPED_NO_MEMORY_SERVICE",
                extra=telemetry_base,
            )
            return

        # Delegate to MemoryService (SRP)
        try:
            await self._memory.index_interaction(
                content=text, user_id=user_id, session_id=conversation_id, role=role
            )
            _RAG_OPS.labels("index_message", "success").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="index_message",
                started_at=start,
                db="qdrant",
                confidence=1.0,
                extra=telemetry_base,
            )
        except Exception as e:
            _RAG_OPS.labels("index_message", "error").inc()
            _RAG_ERRORS.labels("index_message", type(e).__name__).inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="index_message",
                started_at=start,
                db="qdrant",
                confidence=0.0,
                error_code=type(e).__name__,
                extra=telemetry_base,
            )
            # Nao quebrar fluxo do chat se indexacao falhar, mas logar o erro
            logger.warning(
                "Failed to index message for RAG", conversation_id=conversation_id, error=str(e)
            )
        finally:
            _RAG_LATENCY.labels("index_message").observe(time.perf_counter() - start)

    async def maybe_summarize(
        self,
        conversation_id: str,
        role: ModelRole,
        priority: ModelPriority,
        user_id: Optional[str],
        project_id: Optional[str],
        threshold_messages: int = 80,
    ) -> None:
        start = time.perf_counter()
        try:
            conv = self._repo.get_conversation(conversation_id)
            msgs = conv.get("messages", [])
            if len(msgs) < threshold_messages:
                _RAG_SKIPPED.labels("summarize", "below_threshold").inc()
                _RAG_OPS.labels("summarize", "skipped").inc()
                self._emit_step_telemetry(
                    endpoint="/chat/rag",
                    step="summarize",
                    started_at=start,
                    db="llm+chat_repository",
                    confidence=0.0,
                    error_code="SKIPPED_BELOW_THRESHOLD",
                )
                return
            # ja possui summary recente?
            if conv.get("summary"):
                _RAG_SKIPPED.labels("summarize", "already_summarized").inc()
                _RAG_OPS.labels("summarize", "skipped").inc()
                self._emit_step_telemetry(
                    endpoint="/chat/rag",
                    step="summarize",
                    started_at=start,
                    db="llm+chat_repository",
                    confidence=0.0,
                    error_code="SKIPPED_ALREADY_SUMMARIZED",
                )
                return
            # montar texto para sumarizacao
            snippet = []
            for m in msgs[-threshold_messages:]:
                r = m.get("role", "user")
                t = m.get("text", "")
                prefix = "User" if r != "assistant" else "Assistant"
                snippet.append(f"{prefix}: {t}")

            if not snippet:
                _RAG_SKIPPED.labels("summarize", "empty_snippet").inc()
                _RAG_OPS.labels("summarize", "skipped").inc()
                self._emit_step_telemetry(
                    endpoint="/chat/rag",
                    step="summarize",
                    started_at=start,
                    db="llm+chat_repository",
                    confidence=0.0,
                    error_code="SKIPPED_EMPTY_SNIPPET",
                )
                return

            sum_prompt = await get_formatted_prompt(
                "rag_conversation_summary",
                conversation="\n".join(snippet),
            )

            res = await self._llm.invoke_llm(
                prompt=sum_prompt,
                role=ModelRole.KNOWLEDGE_CURATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=30,
                user_id=user_id,
                project_id=project_id,
            )
            summary_text = res.get("response", "")

            # Using to_thread for synchronous repository call
            await asyncio.to_thread(self._repo.update_summary, conversation_id, summary_text)
            _RAG_OPS.labels("summarize", "success").inc()
            self._emit_step_telemetry(
                endpoint="/chat/rag",
                step="summarize",
                started_at=start,
                db="llm+chat_repository",
                confidence=1.0 if str(summary_text or "").strip() else 0.0,
                extra={"message_count": len(msgs), "threshold_messages": int(threshold_messages)},
            )
            logger.info("Conversation summarized successfully", conversation_id=conversation_id)

        except Exception as e:
            _RAG_OPS.labels("summarize", "error").inc()
            _RAG_ERRORS.labels("summarize", type(e).__name__).inc()
            self._emit_step_telemetry(
                endpoint="/chat/rag",
                step="summarize",
                started_at=start,
                db="llm+chat_repository",
                confidence=0.0,
                error_code=type(e).__name__,
                extra={"threshold_messages": int(threshold_messages)},
            )
            logger.error("log_error", message=f"Failed to summarize conversation {conversation_id}: {e}", exc_info=True)
            # Fail silently but log it - summarization is optional
        finally:
            _RAG_LATENCY.labels("summarize").observe(time.perf_counter() - start)
