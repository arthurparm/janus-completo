import asyncio
import hashlib
import os
import time as _time
from typing import Any

import structlog

from app.core.exceptions.chat_exceptions import (
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
)
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.pricing import _provider_pricing
from app.core.monitoring.chat_metrics import (
    CHAT_LATENCY_SECONDS,
    CHAT_MESSAGES_TOTAL,
    CHAT_SPEND_USD_TOTAL,
    CHAT_TOKENS_TOTAL,
)
from app.core.workers.async_consolidation_worker import publish_consolidation_task
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.chat.message_helpers import (
    attach_understanding,
    build_understanding_payload,
    estimate_tokens,
    format_tool_creation_response,
    is_explicit_tool_creation,
    split_ui,
)
from app.services.chat.conversation_service import ConversationService
from app.services.chat_agent_loop import ChatAgentLoop
from app.services.chat_command_handler import ChatCommandHandler
from app.services.outbox_service import OutboxService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService

logger = structlog.get_logger(__name__)


class MessageOrchestrationService:
    def __init__(
        self,
        *,
        repo: ChatRepository,
        llm_service: Any,
        tool_service: Any | None,
        prompt_service: PromptBuilderService,
        rag_service: RAGService | None,
        command_handler: ChatCommandHandler,
        agent_loop: ChatAgentLoop,
        conversation_service: ConversationService,
        outbox_service: OutboxService | None = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._prompt_service = prompt_service
        self._rag_service = rag_service
        self._command_handler = command_handler
        self._agent_loop = agent_loop
        self._conversation_service = conversation_service
        self._outbox_service = outbox_service

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            conv = await asyncio.to_thread(self._repo.get_conversation, conversation_id)
        except ChatRepositoryError as e:
            raise ConversationNotFoundError(str(e)) from e

        self._conversation_service.validate_conversation_access(
            conversation_id, conv, user_id, project_id
        )

        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        size_bytes = 0
        try:
            size_bytes = len(message.encode("utf-8")) if message else 0
        except Exception:
            size_bytes = len(message) if message else 0
        if message and size_bytes > max_bytes:
            raise MessageTooLargeError(size_bytes, max_bytes)
        understanding = build_understanding_payload(message)

        persona = conv.get("persona") or "assistant"
        history = await asyncio.to_thread(self._repo.get_recent_messages, conversation_id, limit=60)
        relevant_memories = None
        if self._rag_service:
            relevant_memories = await self._rag_service.retrieve_context(
                message, user_id=user_id, conversation_id=conversation_id
            )

        prompt = await self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )

        await asyncio.to_thread(self._repo.add_message, conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        in_tokens = estimate_tokens(self._prompt_service, prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)
        try:
            if self._rag_service:
                await self._rag_service.maybe_index_message(
                    text=message, user_id=user_id, conversation_id=conversation_id, role="user"
                )
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to index user message for {conversation_id}: {e}")

        if self._command_handler.is_command(message):
            start_t = _time.time()
            assistant_text = await self._command_handler.handle_command(
                message, conversation_id, user_id
            )
            if assistant_text:
                clean_text, ui = split_ui(assistant_text)
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

                await asyncio.to_thread(
                    self._repo.add_message, conversation_id, role="assistant", text=assistant_text
                )
                out_tokens = estimate_tokens(self._prompt_service, assistant_text)
                CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

                result = {
                    "response": clean_text,
                    "provider": "janus",
                    "model": "quick_command",
                    "role": role.value,
                    "conversation_id": conversation_id,
                }
                if ui:
                    result["ui"] = ui
                return attach_understanding(result, understanding)

        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception as e:
                logger.warning("log_warning", message=f"Failed to trigger summary during discovery for {conversation_id}: {e}"
                )

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "discovery",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_tools_documentation(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "tools_docs",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_local_capabilities(self._tools)
            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "capabilities",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        if self._prompt_service.is_tool_request(message) and is_explicit_tool_creation(message):
            start_t = _time.time()
            if not self._tools:
                assistant_text = "Tool creation is unavailable: tool service is not configured."
            else:
                try:
                    from app.core.evolution import EvolutionManager

                    manager = EvolutionManager(self._llm, self._tools)
                    tool_result = await manager.evolve_tool(message)
                    assistant_text = format_tool_creation_response(tool_result)
                except Exception as e:
                    assistant_text = f"Falha ao criar ferramenta: {e}"

            clean_text, ui = split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = estimate_tokens(self._prompt_service, assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                if self._rag_service:
                    await self._rag_service.maybe_summarize(
                        conversation_id,
                        role=role,
                        priority=priority,
                        user_id=user_id,
                        project_id=project_id,
                    )
            except Exception:
                pass

            result = {
                "response": clean_text,
                "provider": "janus",
                "model": "tool_creation",
                "role": role.value,
            }
            if ui:
                result["ui"] = ui

            result_with_conv = dict(result)
            result_with_conv["conversation_id"] = conversation_id
            try:
                self.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return attach_understanding(result_with_conv, understanding)

        try:
            start_t = _time.time()
            conv = await asyncio.to_thread(self._repo.get_conversation, conversation_id)
            persona = conv.get("persona") or "assistant"
            history = await asyncio.to_thread(
                self._repo.get_recent_messages, conversation_id, limit=20
            )

            relevant_memories = None
            if self._rag_service:
                try:
                    relevant_memories = await self._rag_service.retrieve_context(
                        message, user_id=user_id, conversation_id=conversation_id
                    )
                except Exception as e:
                    logger.warning(
                        "rag_context_retrieval_failed",
                        conversation_id=conversation_id,
                        error=str(e),
                    )

            initial_prompt = await self._prompt_service.build_prompt(
                persona, history, message, conv.get("summary"), relevant_memories
            )

            result = await self._agent_loop.run_loop(
                conversation_id=conversation_id,
                initial_prompt=initial_prompt,
                persona=persona,
                message=message,
                role=role,
                priority=priority,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                project_id=project_id,
            )
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()
        except Exception as e:
            logger.error("Agent loop failed in chat", exc_info=e)
            try:
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="error").inc()
            except Exception:
                pass
            raise ChatServiceError(str(e)) from e

        assistant_text = result.get("response", "")
        clean_text, ui = split_ui(assistant_text)
        await asyncio.to_thread(
            self._repo.add_message, conversation_id, role="assistant", text=assistant_text
        )
        out_tokens = estimate_tokens(self._prompt_service, assistant_text)
        CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

        if self._rag_service:
            try:
                rag_text = clean_text or assistant_text
                await self._rag_service.maybe_index_message(
                    text=rag_text,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="assistant",
                )
            except Exception as e:
                logger.warning(
                    "rag_index_message_failed",
                    conversation_id=conversation_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        try:
            provider = result.get("provider", "unknown")
            pricing = _provider_pricing.get(provider)
            if pricing:
                cost = (in_tokens / 1000.0) * float(pricing.input_per_1k_usd) + (
                    out_tokens / 1000.0
                ) * float(pricing.output_per_1k_usd)
                if user_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="user").inc(cost)
                if project_id:
                    CHAT_SPEND_USD_TOTAL.labels(kind="project").inc(cost)
        except Exception:
            pass

        if self._rag_service:
            try:
                await self._rag_service.maybe_summarize(
                    conversation_id,
                    role=role,
                    priority=priority,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception as e:
                logger.warning(
                    "rag_summarization_failed",
                    conversation_id=conversation_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        result_with_conv = dict(result)
        result_with_conv["conversation_id"] = conversation_id
        result_with_conv["response"] = clean_text
        if ui:
            result_with_conv["ui"] = ui
        try:
            self.trigger_post_response_events(
                conversation_id=conversation_id,
                user_message=message,
                assistant_text=assistant_text,
                result=result,
                user_id=user_id,
                project_id=project_id,
            )
        except Exception:
            pass
        return attach_understanding(result_with_conv, understanding)

    def trigger_post_response_events(
        self,
        conversation_id: str,
        user_message: str,
        assistant_text: str,
        result: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        try:
            digest = hashlib.sha256(
                f"{conversation_id}:{assistant_text}".encode("utf-8")
            ).hexdigest()[:16]
            experience_id = f"{conversation_id}:{digest}"
            dedupe_key = f"consolidation:{conversation_id}:{digest}"
            consolidation_payload = {
                "mode": "single",
                "experience_id": experience_id,
                "experience_content": assistant_text,
                "metadata": {
                    "conversation_id": conversation_id,
                    "role": result.get("role"),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "user_message": (user_message or "")[:500],
                    "user_id": user_id,
                    "project_id": project_id,
                    "dedupe_key": dedupe_key,
                },
            }
            if self._outbox_service:
                self._outbox_service.enqueue_consolidation(
                    payload=consolidation_payload,
                    aggregate_id=conversation_id,
                    dedupe_key=dedupe_key,
                )
            else:
                asyncio.create_task(
                    publish_consolidation_task(consolidation_payload, correlation_id=conversation_id)
                )
        except Exception:
            pass
