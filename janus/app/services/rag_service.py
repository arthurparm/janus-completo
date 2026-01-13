import asyncio
import structlog
from typing import Optional

from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_repository import ChatRepository
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


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

    async def retrieve_context(self, message: str, limit: int = 5) -> Optional[str]:
        """Retrieves relevant memories for the current message."""
        if not self._memory:
            return None

        try:
            memories = await self._memory.recall_experiences(
                query=message, limit=limit, min_score=0.3
            )
            if memories:
                memory_lines = []
                for m in memories:
                    content = (
                        m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
                    )
                    mem_type = (
                        m.get("type", "memory")
                        if isinstance(m, dict)
                        else getattr(m, "type", "memory")
                    )
                    # Truncate long content
                    content_preview = content[:500] + "..." if len(content) > 500 else content
                    memory_lines.append(f"- [{mem_type}]: {content_preview}")

                logger.info("RAG enrichment: retrieved %d relevant memories", len(memories))
                return "\n".join(memory_lines)
        except Exception as e:
            logger.warning("Failed to retrieve memories for prompt enrichment", error=str(e))
            # We don't raise here to prevent blocking the chat response if memory fails
            return None

        return None

    async def maybe_index_message(
        self, text: str, user_id: Optional[str], conversation_id: str, role: str
    ) -> None:
        if not text or not user_id or not self._memory:
            return

        # Delegate to MemoryService (SRP)
        try:
            await self._memory.index_interaction(
                content=text, user_id=user_id, session_id=conversation_id, role=role
            )
        except Exception as e:
            # Não quebrar fluxo do chat se indexação falhar, mas logar o erro
            logger.warning(
                "Failed to index message for RAG", conversation_id=conversation_id, error=str(e)
            )

    async def maybe_summarize(
        self,
        conversation_id: str,
        role: ModelRole,
        priority: ModelPriority,
        user_id: Optional[str],
        project_id: Optional[str],
        threshold_messages: int = 80,
    ) -> None:
        try:
            conv = self._repo.get_conversation(conversation_id)
            msgs = conv.get("messages", [])
            if len(msgs) < threshold_messages:
                return
            # já possui summary recente?
            if conv.get("summary"):
                return
            # montar texto para sumarização
            snippet = []
            for m in msgs[-threshold_messages:]:
                r = m.get("role", "user")
                t = m.get("text", "")
                prefix = "User" if r != "assistant" else "Assistant"
                snippet.append(f"{prefix}: {t}")

            if not snippet:
                return

            sum_prompt = (
                "Summarize the following conversation succinctly to preserve context:\n"
                + "\n".join(snippet)
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
            logger.info("Conversation summarized successfully", conversation_id=conversation_id)

        except Exception as e:
            logger.error(f"Failed to summarize conversation {conversation_id}: {e}", exc_info=True)
            # Fail silently but log it - summarization is optional
