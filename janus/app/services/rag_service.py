import asyncio
import time
from typing import Any, Optional

import structlog
from qdrant_client import models as qdrant_models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm import ModelPriority, ModelRole
from app.core.ui.generative_ui import extract_ui_block
from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client
from app.repositories.chat_repository import ChatRepository
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService

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
_RAG_RESULTS = Counter("rag_service_results_total", "RAG result items", ["operation"])


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
                mem_type = m.get("type") or (m.get("metadata") or {}).get("type") or "memory"
            else:
                content = getattr(m, "content", "") or ""
                mem_type = getattr(m, "type", "memory")

            if not content:
                continue
            content_preview = content[:500] + "..." if len(content) > 500 else content
            memory_lines.append(f"- [{mem_type}]: {content_preview}")

        return "\n".join(memory_lines) if memory_lines else None

    async def retrieve_context(
        self,
        message: str,
        limit: int = 5,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Optional[str]:
        """Retrieves relevant memories for the current message."""
        if not self._memory:
            _RAG_SKIPPED.labels("retrieve_context", "no_memory_service").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            return None
        if not message:
            _RAG_SKIPPED.labels("retrieve_context", "empty_message").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            return None
        if not user_id:
            logger.debug("RAG context skipped: missing user_id")
            _RAG_SKIPPED.labels("retrieve_context", "missing_user_id").inc()
            _RAG_OPS.labels("retrieve_context", "skipped").inc()
            return None

        start = time.perf_counter()
        try:
            vec = await aembed_text(message)
            collection_name = await aget_or_create_collection(f"user_{user_id}")
            client = get_async_qdrant_client()

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
                limit=limit,
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

            _RAG_OPS.labels("retrieve_context", "success").inc()
            if memories:
                _RAG_RESULTS.labels("retrieve_context").inc(len(memories))
                logger.info("RAG enrichment: retrieved %d relevant memories", len(memories))
                _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
                return self._format_memories(memories)

            _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
            return None
        except Exception as e:
            _RAG_OPS.labels("retrieve_context", "error").inc()
            _RAG_ERRORS.labels("retrieve_context", type(e).__name__).inc()
            _RAG_LATENCY.labels("retrieve_context").observe(time.perf_counter() - start)
            logger.warning("Failed to retrieve memories for prompt enrichment", error=str(e))
            # We don't raise here to prevent blocking the chat response if memory fails
            return None

    async def maybe_index_message(
        self, text: str, user_id: Optional[str], conversation_id: str, role: str
    ) -> None:
        if not text:
            _RAG_SKIPPED.labels("index_message", "empty_text").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            return
        if not user_id:
            _RAG_SKIPPED.labels("index_message", "missing_user_id").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            return
        if not self._memory:
            _RAG_SKIPPED.labels("index_message", "no_memory_service").inc()
            _RAG_OPS.labels("index_message", "skipped").inc()
            return

        # Delegate to MemoryService (SRP)
        start = time.perf_counter()
        try:
            await self._memory.index_interaction(
                content=text, user_id=user_id, session_id=conversation_id, role=role
            )
            _RAG_OPS.labels("index_message", "success").inc()
        except Exception as e:
            _RAG_OPS.labels("index_message", "error").inc()
            _RAG_ERRORS.labels("index_message", type(e).__name__).inc()
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
                return
            # ja possui summary recente?
            if conv.get("summary"):
                _RAG_SKIPPED.labels("summarize", "already_summarized").inc()
                _RAG_OPS.labels("summarize", "skipped").inc()
                return
            # montar texto para sumarizacao
            snippet = []
            for m in msgs[-threshold_messages:]:
                r = m.get("role", "user")
                t = m.get("text", "")
                clean_text, _ = extract_ui_block(t)
                prefix = "User" if r != "assistant" else "Assistant"
                snippet.append(f"{prefix}: {clean_text}")

            if not snippet:
                _RAG_SKIPPED.labels("summarize", "empty_snippet").inc()
                _RAG_OPS.labels("summarize", "skipped").inc()
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
            logger.info("Conversation summarized successfully", conversation_id=conversation_id)

        except Exception as e:
            _RAG_OPS.labels("summarize", "error").inc()
            _RAG_ERRORS.labels("summarize", type(e).__name__).inc()
            logger.error(f"Failed to summarize conversation {conversation_id}: {e}", exc_info=True)
            # Fail silently but log it - summarization is optional
        finally:
            _RAG_LATENCY.labels("summarize").observe(time.perf_counter() - start)
