import asyncio
import re
import time
from typing import Any, Optional

import structlog

from qdrant_client import models as qdrant_models

from app.config import settings
from app.core.embeddings.embedding_manager import aembed_text
from app.core.llm import ModelPriority, ModelRole
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.memory.rag_telemetry import confidence_from_scores, emit_step_telemetry
from app.core.routing import RouteDecision, RouteIntent, RouteTarget, get_knowledge_routing_policy
from app.db.vector_store import (
    aget_or_create_collection,
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    get_async_qdrant_client,
)
from app.repositories.chat_repository import ChatRepository
from app.services.procedural_memory_service import procedural_memory_service
from app.services.secret_memory_service import secret_memory_service
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
            metadata: dict[str, Any] = {}
            if isinstance(m, dict):
                content = (
                    m.get("content", "")
                    or (m.get("payload") or {}).get("content", "")
                    or m.get("page_content", "")
                )
                metadata = (m.get("metadata") or {}) if isinstance(m.get("metadata"), dict) else {}
                mem_type = (
                    m.get("type")
                    or metadata.get("type")
                    or "memory"
                )
            else:
                content = getattr(m, "content", "") or ""
                mem_type = getattr(m, "type", "memory")

            if not content:
                continue
            content_preview = content[:500] + "..." if len(content) > 500 else content
            label = mem_type
            if mem_type == "doc_chunk":
                file_name = str(
                    metadata.get("file_name")
                    or metadata.get("title")
                    or metadata.get("doc_id")
                    or ""
                ).strip()
                if file_name:
                    label = f"{mem_type}:{file_name}"
            memory_lines.append(f"- [{label}]: {content_preview}")

        return "\n".join(memory_lines) if memory_lines else None

    def _format_memory_block(self, title: str, items: list[str]) -> str | None:
        cleaned = [str(item).strip() for item in items if str(item or "").strip()]
        if not cleaned:
            return None
        return "\n".join([title, *cleaned])

    def _format_episodic_context(self, memories: list[dict[str, Any]]) -> str | None:
        lines: list[str] = []
        for memory in memories[:5]:
            content = str(memory.get("content") or "").strip()
            if not content:
                continue
            preview = content[:320].rstrip()
            if len(content) > 320:
                preview = f"{preview}..."
            role = str((memory.get("metadata") or {}).get("role") or "").strip()
            prefix = f"{role}: " if role else ""
            lines.append(f"- {prefix}{preview}")
        guidance = [
            "- Use este bloco como contexto situacional recente.",
            "- Não deixe fatos episódicos sobreporem instruções persistentes do usuário.",
        ]
        return self._format_memory_block("Contexto Recente Relevante:", [*guidance, *lines])

    def _merge_memory_sections(self, sections: list[str | None]) -> str | None:
        cleaned = [str(section).strip() for section in sections if str(section or "").strip()]
        if not cleaned:
            return None
        return "\n\n".join(cleaned)

    def _score_episodic_memory(
        self,
        item: dict[str, Any],
        *,
        conversation_id: str | None,
    ) -> float:
        metadata = item.get("metadata") or {}
        score = float(item.get("score") or 0.0)
        if conversation_id and str(metadata.get("conversation_id") or "") == str(conversation_id):
            score += 1.25
        ts_ms = metadata.get("ts_ms") or metadata.get("timestamp")
        try:
            age_hours = max(0.0, (int(time.time() * 1000) - int(ts_ms)) / 3_600_000.0)
        except Exception:
            age_hours = 72.0
        score += max(0.0, 0.8 - min(age_hours / 72.0, 0.8))
        return score

    async def _retrieve_episodic_context(
        self,
        *,
        message: str,
        user_id: str,
        conversation_id: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        vec = await aembed_text(message)
        client = get_async_qdrant_client()
        candidate_multiplier = max(1, int(getattr(settings, "RAG_RERANK_CANDIDATE_MULTIPLIER", 3)))
        query_limit = (
            max(int(limit), int(limit) * candidate_multiplier)
            if bool(getattr(settings, "RAG_RERANK_ENABLED", True))
            else int(limit)
        )
        coll = await aget_or_create_collection(build_user_chat_collection_name(str(user_id)))
        res = await client.query_points(
            collection_name=coll,
            query=vec,
            limit=query_limit,
            with_payload=True,
            query_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="metadata.user_id",
                        match=qdrant_models.MatchValue(value=str(user_id)),
                    )
                ]
            ),
        )
        hits = list(getattr(res, "points", res) or [])
        memories = [
            {
                "content": (getattr(hit, "payload", {}) or {}).get("content", ""),
                "metadata": (getattr(hit, "payload", {}) or {}).get("metadata") or {},
                "type": ((getattr(hit, "payload", {}) or {}).get("metadata") or {}).get("type", "chat_msg"),
                "score": getattr(hit, "score", None),
            }
            for hit in hits
        ]
        rerank_applied = False
        rerank_method = "none"
        rerank_candidate_count = len(memories)
        if memories:
            rerank_result = await self._reranker.rerank(query=message, items=memories, top_k=limit)
            memories = rerank_result.items
            rerank_applied = rerank_result.applied
            rerank_method = rerank_result.method
            rerank_candidate_count = int(rerank_result.candidate_count)
        ranked = sorted(
            memories,
            key=lambda item: self._score_episodic_memory(item, conversation_id=conversation_id),
            reverse=True,
        )[:limit]
        return ranked, {
            "query_limit": int(query_limit),
            "rerank_applied": rerank_applied,
            "rerank_method": rerank_method,
            "rerank_candidate_count": int(rerank_candidate_count),
            "rerank_top_k": int(limit),
        }

    async def _retrieve_semantic_context(
        self,
        *,
        message: str,
        user_id: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        items = await user_preference_memory_service.list_preferences(
            user_id=str(user_id),
            query=message,
            limit=min(5, max(1, limit)),
            active_only=True,
        )
        return items, user_preference_memory_service.format_preference_context(items)

    async def _retrieve_procedural_context(
        self,
        *,
        message: str,
        user_id: str,
        conversation_id: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        items = await procedural_memory_service.list_rules(
            user_id=str(user_id),
            conversation_id=conversation_id,
            query=message,
            limit=min(5, max(1, limit)),
            active_only=True,
        )
        return items, procedural_memory_service.format_procedural_context(items)

    def _references_uploaded_material(self, message: str) -> bool:
        text = (message or "").lower()
        patterns = (
            r"\barquivo\b",
            r"\banexo\b",
            r"\bdocumento\b",
            r"\bupload\b",
            r"\benviei\b",
            r"\bmandei\b",
            r"\bte mandei\b",
            r"\battachment\b",
            r"\battached\b",
            r"\bsent\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    async def _conversation_document_context(
        self,
        *,
        user_id: str,
        conversation_id: str,
        limit: int = 3,
    ) -> str | None:
        client = get_async_qdrant_client()
        collection_name = await aget_or_create_collection(build_user_docs_collection_name(str(user_id)))
        scroll_res = await client.scroll(
            collection_name=collection_name,
            scroll_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_models.MatchValue(value="doc_chunk"),
                    ),
                    qdrant_models.FieldCondition(
                        key="metadata.user_id",
                        match=qdrant_models.MatchValue(value=str(user_id)),
                    ),
                    qdrant_models.FieldCondition(
                        key="metadata.conversation_id",
                        match=qdrant_models.MatchValue(value=str(conversation_id)),
                    ),
                ]
            ),
            limit=max(limit * 8, limit),
            with_payload=True,
        )
        points = scroll_res[0] if isinstance(scroll_res, tuple) else (scroll_res or [])
        docs: dict[str, dict[str, Any]] = {}
        for point in points:
            payload = getattr(point, "payload", {}) or {}
            metadata = payload.get("metadata") or {}
            doc_id = str(metadata.get("doc_id") or "").strip()
            if not doc_id:
                continue
            current = docs.get(doc_id)
            if current is None:
                docs[doc_id] = {
                    "file_name": metadata.get("file_name") or doc_id,
                    "summary": metadata.get("semantic_summary") or "",
                    "preview": str(payload.get("content") or "").strip(),
                }
            if len(docs) >= limit:
                break
        if not docs:
            return None
        lines = ["Documentos anexados nesta conversa:"]
        for item in list(docs.values())[:limit]:
            detail = str(item.get("summary") or item.get("preview") or "").strip()
            if len(detail) > 180:
                detail = f"{detail[:177].rstrip()}..."
            if detail:
                lines.append(f"- {item.get('file_name')}: {detail}")
            else:
                lines.append(f"- {item.get('file_name')}")
        return "\n".join(lines)

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
        route_decision: RouteDecision | None = None,
    ) -> Optional[str]:
        """Retrieves relevant memories for the current message."""
        start = time.perf_counter()
        resolved_route = route_decision or get_knowledge_routing_policy().resolve(
            RouteIntent.CHAT_CONTEXT_RETRIEVAL,
            user_id=user_id,
            include_graph=False,
            query=message,
        )
        route_meta = {
            "route.rule_id": resolved_route.rule_id,
            "route.primary": resolved_route.primary.value,
            "route.fallback": resolved_route.fallback,
        }
        telemetry_base = {
            "transport": transport,
            "identity_source": identity_source,
            "user_id_present": bool(user_id),
            "conversation_id_present": bool(conversation_id),
            **route_meta,
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
        if resolved_route.primary != RouteTarget.QDRANT:
            _RAG_SKIPPED.labels("retrieve_context", "route_not_supported").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            self._emit_step_telemetry(
                endpoint=caller_endpoint,
                step="retrieve_context",
                started_at=start,
                db=resolved_route.primary.value,
                confidence=0.0,
                error_code="SKIPPED_ROUTE_UNSUPPORTED",
                extra=telemetry_base,
            )
            return None

        try:
            episodic_items, episodic_meta = await self._retrieve_episodic_context(
                message=message,
                user_id=str(user_id),
                conversation_id=conversation_id,
                limit=limit,
            )
            semantic_items, semantic_context = await self._retrieve_semantic_context(
                message=message,
                user_id=str(user_id),
                limit=limit,
            )
            procedural_items, procedural_context = await self._retrieve_procedural_context(
                message=message,
                user_id=str(user_id),
                conversation_id=conversation_id,
                limit=limit,
            )
            episodic_context = self._format_episodic_context(episodic_items)
            secret_context = None
            secret_items: list[dict[str, Any]] = []
            if secret_memory_service.should_authorize_prompt_recall(message):
                secret_context = await secret_memory_service.build_authorized_prompt_context(
                    user_id=str(user_id),
                    message=message,
                    conversation_id=conversation_id,
                    limit=min(3, max(1, limit)),
                )
                secret_items = await secret_memory_service.list_secrets(
                    user_id=str(user_id),
                    query=message,
                    conversation_id=conversation_id,
                    limit=min(3, max(1, limit)),
                    reveal=False,
                )

            combined_context = self._merge_memory_sections(
                [
                    secret_context,
                    procedural_context,
                    semantic_context,
                    episodic_context,
                ]
            )
            if conversation_id and self._references_uploaded_material(message):
                try:
                    conversation_doc_context = await self._conversation_document_context(
                        user_id=str(user_id),
                        conversation_id=str(conversation_id),
                    )
                except Exception as doc_exc:
                    logger.warning("rag_conversation_document_context_failed", error=str(doc_exc))
                    conversation_doc_context = None
                combined_context = self._merge_memory_sections(
                    [conversation_doc_context, combined_context]
                )

            _RAG_OPS.labels("retrieve_context", "success").inc()
            scores = [m.get("score") for m in episodic_items]
            if combined_context:
                total_items = len(episodic_items) + len(semantic_items) + len(procedural_items) + len(secret_items)
                _RAG_RESULTS.labels("retrieve_context").inc(total_items)
                logger.info("RAG enrichment: retrieved %d relevant memories", total_items)
                _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
                self._emit_step_telemetry(
                    endpoint=caller_endpoint,
                    step="retrieve_context",
                    started_at=start,
                    db="qdrant",
                    confidence=confidence_from_scores(scores),
                    extra={
                        **telemetry_base,
                        "result_count": total_items,
                        "limit": int(limit),
                        "query_limit": int(episodic_meta["query_limit"]),
                        "rerank_applied": episodic_meta["rerank_applied"],
                        "rerank_method": episodic_meta["rerank_method"],
                        "rerank_candidate_count": int(episodic_meta["rerank_candidate_count"]),
                        "rerank_top_k": int(episodic_meta["rerank_top_k"]),
                        "episodic_count": len(episodic_items),
                        "user_preferences_count": len(semantic_items),
                        "procedural_memory_count": len(procedural_items),
                        "authorized_secret_count": len(secret_items),
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
                    "query_limit": int(episodic_meta["query_limit"]),
                    "rerank_applied": episodic_meta["rerank_applied"],
                    "rerank_method": episodic_meta["rerank_method"],
                    "rerank_candidate_count": int(episodic_meta["rerank_candidate_count"]),
                    "rerank_top_k": int(episodic_meta["rerank_top_k"]),
                    "user_preferences_count": len(semantic_items),
                    "procedural_memory_count": len(procedural_items),
                    "authorized_secret_count": len(secret_items),
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
