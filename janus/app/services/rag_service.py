import asyncio

import structlog

from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_repository import ChatRepository
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


class RAGService:
    """
    Service responsible for Retrieval-Augmented Generation (RAG) operations,
    including memory retrieval, indexing, and conversation summarization.
    """

    def __init__(
        self,
        repo: ChatRepository,
        llm_service: LLMService,
        memory_service: MemoryService | None = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._memory = memory_service

    async def retrieve_context(self, message: str, limit: int = 5) -> str | None:
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
                        m.get("content", "")
                        if isinstance(m, dict)
                        else getattr(m, "content", "")
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

        return None

    async def maybe_index_message(
        self, text: str, user_id: str | None, conversation_id: str, role: str
    ) -> None:
        if not text or not user_id or not self._memory:
            return

        # Delegate to MemoryService (SRP)
        try:
            await self._memory.index_interaction(
                content=text, user_id=user_id, session_id=conversation_id, role=role
            )
        except Exception:
            # Não quebrar fluxo do chat se indexação falhar
            pass

    async def maybe_summarize(
        self,
        conversation_id: str,
        role: ModelRole,
        priority: ModelPriority,
        user_id: str | None,
        project_id: str | None,
        threshold_messages: int = 80,
    ) -> None:
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
        sum_prompt = (
            "Summarize the following conversation succinctly to preserve context:\n"
            + "\n".join(snippet)
        )
        try:
            res = await asyncio.to_thread(
                self._llm.invoke_llm,
                prompt=sum_prompt,
                role=ModelRole.KNOWLEDGE_CURATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=30,
                user_id=user_id,
                project_id=project_id,
            )
            summary_text = res.get("response", "")
            await asyncio.to_thread(self._repo.update_summary, conversation_id, summary_text)
        except Exception as e:
            logger.error(f"Failed to summarize conversation {conversation_id}: {e}", exc_info=True)
            # Fail silently but log it - summarization is optional but we need to know why it failed
