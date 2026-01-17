import asyncio
import json
import os
import time as _time
from typing import Any
from uuid import uuid4

import structlog
from fastapi import Request

from app.core.infrastructure.message_broker import get_broker
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.llm_manager import _provider_pricing  # type: ignore
from app.core.monitoring.chat_metrics import (
    CHAT_LATENCY_SECONDS,
    CHAT_MESSAGES_TOTAL,
    CHAT_SPEND_USD_TOTAL,
    CHAT_TOKENS_TOTAL,
    update_active_conversations,
)
from app.core.ui.generative_ui import extract_ui_block
from app.core.workers.async_consolidation_worker import publish_consolidation_task
from app.core.exceptions.chat_exceptions import (
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
    PromptBuildError,
)
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.memory_service import MemoryService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.tool_executor_service import ToolExecutorService
from app.services.tool_service import ToolService

# New modular services
from app.services.chat_command_handler import ChatCommandHandler
from app.services.chat_event_publisher import ChatEventPublisher
from app.services.chat_agent_loop import ChatAgentLoop

logger = structlog.get_logger(__name__)


# Exceptions moved to app.core.exceptions.chat_exceptions


class ChatService:
    """
    Orchestrates chat conversations, composing prompts with persona and history,
    delegating LLM invocation to LLMService, and storing messages in ChatRepository.
    """

    def __init__(
        self,
        repo: ChatRepository,
        llm_service: LLMService,
        tool_service: ToolService | None = None,
        memory_service: MemoryService | None = None,
        prompt_service: PromptBuilderService | None = None,
        tool_executor_service: ToolExecutorService | None = None,
        rag_service: RAGService | None = None,
        event_logger: Any | None = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._memory = memory_service

        # Core services
        self._prompt_service = prompt_service or PromptBuilderService()
        self._tool_executor = tool_executor_service or ToolExecutorService()

        # RAGService setup
        if rag_service:
            self._rag_service = rag_service
        elif memory_service:
            self._rag_service = RAGService(repo, llm_service, memory_service)
        else:
            self._rag_service = None

        # New modular services (Phase 2 refactoring)
        self._command_handler = ChatCommandHandler(tool_service, memory_service)
        self._event_publisher = ChatEventPublisher(db_logger=None)  # TODO: inject DB logger
        if event_logger is not None:
            self._event_publisher = ChatEventPublisher(db_logger=event_logger)
        self._agent_loop = ChatAgentLoop(
            llm_service=llm_service,
            tool_executor=self._tool_executor,
            rag_service=self._rag_service,
            event_publisher=self._event_publisher,
            prompt_service=self._prompt_service,
        )

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            est = self._prompt_service.estimate_tokens(text)
            if isinstance(est, int) and est > 0:
                return est
        except Exception:
            pass
        return max(1, len(text) // 4)

    def _split_ui(self, text: str) -> tuple[str, dict[str, Any] | None]:
        return extract_ui_block(text)

    def _is_explicit_tool_creation(self, message: str) -> bool:
        if not message:
            return False
        lower = message.lower()
        if "tool" not in lower and "ferramenta" not in lower:
            return False
        creation_keywords = ("crie", "criar", "create", "build", "gerar", "generate")
        return any(k in lower for k in creation_keywords)

    def _format_tool_creation_response(self, result: dict[str, Any]) -> str:
        if not result:
            return "Tool creation returned an empty result."
        name = result.get("name") or result.get("tool_name") or result.get("tool") or "unknown"
        status = result.get("evolution_message") or "Tool creation completed."
        payload = json.dumps(result, indent=2, ensure_ascii=False)
        return f"{status}\n\nTool: {name}\n\n{payload}"

    def _validate_conversation_access(
        self,
        conversation_id: str,
        conv: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        conv_user_id = conv.get("user_id")
        if user_id and conv_user_id and str(conv_user_id) != str(user_id):
            raise ChatServiceError("Access denied: user_id mismatch")
        conv_project_id = conv.get("project_id")
        if project_id and conv_project_id and str(conv_project_id) != str(project_id):
            raise ChatServiceError("Access denied: project_id mismatch")

    async def _publish_agent_event(
        self,
        conversation_id: str,
        event_type: str,
        agent_role: str,
        content: str,
        task_id: str | None = None,
        user_id: str | None = None,
    ):
        """Publish agent event using ChatEventPublisher (Phase 2 refactoring)."""
        await self._event_publisher.publish_event(
            conversation_id=conversation_id,
            event_type=event_type,
            agent_role=agent_role,
            content=content,
            task_id=task_id,
            user_id=user_id,
        )

    async def start_conversation(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        cid = await asyncio.to_thread(self._repo.start_conversation, persona, user_id, project_id)
        try:
            count = await asyncio.to_thread(self._repo.count_conversations)
            update_active_conversations(count)
        except Exception as e:
            logger.warning(f"Failed to update active conversation metrics: {e}")
        return cid

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

        self._validate_conversation_access(conversation_id, conv, user_id, project_id)

        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        size_bytes = 0
        try:
            size_bytes = len(message.encode("utf-8")) if message else 0
        except Exception:
            size_bytes = len(message) if message else 0
        if message and size_bytes > max_bytes:
            raise MessageTooLargeError(size_bytes, max_bytes)

        persona = conv.get("persona") or "assistant"
        history = await asyncio.to_thread(self._repo.get_recent_messages, conversation_id, limit=60)
        # RAG Logic
        relevant_memories = None
        if self._rag_service:
            relevant_memories = await self._rag_service.retrieve_context(
                message, user_id=user_id, conversation_id=conversation_id
            )

        prompt = await self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )

        # Store user message before invocation
        await asyncio.to_thread(self._repo.add_message, conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        in_tokens = self._prompt_service.estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)
        try:
            if self._rag_service:
                await self._rag_service.maybe_index_message(
                    text=message, user_id=user_id, conversation_id=conversation_id, role="user"
                )
        except Exception as e:
            logger.warning(f"Failed to index user message for {conversation_id}: {e}")

        # Quick Commands (Quick Win) - Use ChatCommandHandler (Phase 2 refactoring)
        if self._command_handler.is_command(message):
            start_t = _time.time()
            assistant_text = await self._command_handler.handle_command(
                message, conversation_id, user_id
            )
            if assistant_text:
                clean_text, ui = self._split_ui(assistant_text)
                elapsed = max(0.0, _time.time() - start_t)
                CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
                CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

                # Store assistant response
                # Store assistant response
                await asyncio.to_thread(
                    self._repo.add_message, conversation_id, role="assistant", text=assistant_text
                )
                out_tokens = self._prompt_service.estimate_tokens(assistant_text)
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
                return result

        # Intercepta fluxo de descoberta interativa de ferramentas/configuração
        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
            _clean_text, ui = self._split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
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
                logger.warning(
                    f"Failed to trigger summary during discovery for {conversation_id}: {e}"
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
            # Disparar gatilhos pós-resposta
            try:
                self._trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return result_with_conv

        # Intercepta geração automática de documentação das ferramentas
        if self._prompt_service.is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_tools_documentation(self._tools)
            clean_text, ui = self._split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            # Summarização automática se histórico for grande
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
            # Disparar gatilhos pós-resposta
            try:
                self._trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return result_with_conv

        # Intercepta perguntas sobre capacidades/ferramentas e responde com dados locais
        if self._prompt_service.is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_local_capabilities(self._tools)
            clean_text, ui = self._split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            # Store assistant response
            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            # Summarização automática se histórico for grande
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
            # Disparar gatilhos pós-resposta
            try:
                self._trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return result_with_conv

        # Intercepta solicitaÇõÇœes de criaÇõÇœo de ferramentas
        if self._prompt_service.is_tool_request(message) and self._is_explicit_tool_creation(message):
            start_t = _time.time()
            if not self._tools:
                assistant_text = "Tool creation is unavailable: tool service is not configured."
            else:
                try:
                    from app.core.evolution import EvolutionManager

                    manager = EvolutionManager(self._llm, self._tools)
                    tool_result = await manager.evolve_tool(message)
                    assistant_text = self._format_tool_creation_response(tool_result)
                except Exception as e:
                    assistant_text = f"Falha ao criar ferramenta: {e}"

            clean_text, ui = self._split_ui(assistant_text)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="success").inc()

            await asyncio.to_thread(
                self._repo.add_message, conversation_id, role="assistant", text=assistant_text
            )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
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
                self._trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass
            return result_with_conv

        # Agent Loop Execution (Phase 2 refactoring - using ChatAgentLoop service)
        try:
            start_t = _time.time()

            # Get conversation context for agent loop
            conv = await asyncio.to_thread(self._repo.get_conversation, conversation_id)
            persona = conv.get("persona") or "assistant"
            history = await asyncio.to_thread(
                self._repo.get_recent_messages, conversation_id, limit=20
            )

            # RAG: Retrieve relevant memories
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
                    # Continue without RAG context - graceful degradation

            # Build initial prompt
            initial_prompt = await self._prompt_service.build_prompt(
                persona, history, message, conv.get("summary"), relevant_memories
            )

            # Run agent loop with new service
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

        # Store assistant response
        assistant_text = result.get("response", "")
        clean_text, ui = self._split_ui(assistant_text)
        await asyncio.to_thread(
            self._repo.add_message, conversation_id, role="assistant", text=assistant_text
        )
        out_tokens = self._prompt_service.estimate_tokens(assistant_text)
        CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
        # Index assistant message for RAG (non-blocking)
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

        # Aproxima custo com pricing do provedor, se disponível
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

        # Automatic summarization (non-blocking)
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
        # Disparar gatilhos pós-resposta
        try:
            self._trigger_post_response_events(
                conversation_id=conversation_id,
                user_message=message,
                assistant_text=assistant_text,
                result=result,
                user_id=user_id,
                project_id=project_id,
            )
        except Exception:
            pass
        return result_with_conv

    def get_history(
        self,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        logger.info(f"Getting chat history for conversation: {conversation_id}")
        try:
            conv = self._repo.get_conversation(conversation_id)
            self._validate_conversation_access(conversation_id, conv, user_id, project_id)

            # Validar estrutura da conversa
            if not isinstance(conv, dict):
                logger.error(
                    f"Invalid conversation structure for {conversation_id}: expected dict, got {type(conv)}"
                )
                raise ConversationNotFoundError(
                    f"Invalid conversation structure for {conversation_id}"
                )

            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                logger.warning(
                    f"Messages is not a list for conversation {conversation_id}, converting to empty list"
                )
                messages = []

            logger.info(
                f"Successfully retrieved conversation {conversation_id} with {len(messages)} messages"
            )

            return {
                "conversation_id": conversation_id,
                "persona": conv.get("persona"),
                "messages": messages,
            }

        except ChatRepositoryError as e:
            logger.error(f"Repository error getting conversation {conversation_id}: {e}")
            raise ConversationNotFoundError(str(e)) from e
        except Exception as e:
            logger.error(
                f"Unexpected error getting history for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            raise ChatServiceError(
                f"Failed to get history for conversation {conversation_id}: {e!s}"
            )

    def get_history_paginated(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        before_ts: float | None = None,
        after_ts: float | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retorna histórico de mensagens com paginação e validação de acesso.

        Args:
            conversation_id: ID da conversa
            limit: Número máximo de mensagens (padrão 50, max 200)
            offset: Número de mensagens a pular
            before_ts: Timestamp para buscar mensagens antes desta data
            after_ts: Timestamp para buscar mensagens após esta data
            user_id: ID do usuário para validação de acesso
            project_id: ID do projeto para validação de acesso

        Returns:
            Dict com mensagens paginadas e metadados
        """
        logger.info(
            f"Getting paginated chat history for conversation: {conversation_id}, limit: {limit}, offset: {offset}"
        )

        try:
            # Validar limit máximo
            limit = min(limit, 200)

            # Obter dados da conversa para validação
            conv = self._repo.get_conversation(conversation_id)

            # Validar estrutura da conversa
            if not isinstance(conv, dict):
                logger.error(
                    f"Invalid conversation structure for {conversation_id}: expected dict, got {type(conv)}"
                )
                raise ConversationNotFoundError(
                    f"Invalid conversation structure for {conversation_id}"
                )

            self._validate_conversation_access(conversation_id, conv, user_id, project_id)

            # Obter histórico paginado
            result = self._repo.get_history_paginated(
                conversation_id, limit=limit, offset=offset, before_ts=before_ts, after_ts=after_ts
            )

            logger.info(
                f"Successfully retrieved paginated history for conversation {conversation_id}: "
                f"{len(result['messages'])} messages (total: {result['total_count']})"
            )

            return {
                "conversation_id": conversation_id,
                "persona": conv.get("persona"),
                "messages": result["messages"],
                "total_count": result["total_count"],
                "has_more": result["has_more"],
                "next_offset": result["next_offset"],
                "limit": result["limit"],
                "offset": result["offset"],
            }

        except ChatRepositoryError as e:
            logger.error(f"Repository error getting paginated history for {conversation_id}: {e}")
            raise ConversationNotFoundError(str(e)) from e
        except Exception as e:
            logger.error(
                f"Unexpected error getting paginated history for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            raise ChatServiceError(
                f"Failed to get paginated history for conversation {conversation_id}: {e!s}"
            )

    # Conversas: list/rename/delete com RBAC básico
    async def list_conversations(
        self, user_id: str | None = None, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            self._repo.list_conversations, user_id=user_id, project_id=project_id, limit=limit
        )
        return result

    async def rename_conversation(
        self,
        conversation_id: str,
        new_title: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.rename_conversation,
                conversation_id,
                new_title,
                user_id=user_id,
                project_id=project_id,
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    async def delete_conversation(
        self, conversation_id: str, user_id: str | None = None, project_id: str | None = None
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.delete_conversation,
                conversation_id,
                user_id=user_id,
                project_id=project_id,
            )
            try:
                count = await asyncio.to_thread(self._repo.count_conversations)
                update_active_conversations(count)
            except Exception:
                pass
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    async def update_message(
        self, conversation_id: str, message_id: int, new_text: str, user_id: str | None = None
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.update_message_text,
                conversation_id,
                message_id,
                new_text,
                user_id=user_id,
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    async def delete_message(
        self, conversation_id: str, message_id: int, user_id: str | None = None
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.delete_message, conversation_id, message_id, user_id=user_id
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e))

    # Streaming helper: retorna generator de eventos SSE (strings já formatadas)
    async def stream_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole | None = None,
        priority: ModelPriority | None = None,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
    ):
        role = role or ModelRole.ORCHESTRATOR
        priority = priority or ModelPriority.HIGH_QUALITY

        # Config
        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        default_timeout = int(os.getenv("CHAT_DEFAULT_TIMEOUT_SECONDS", "30"))
        heartbeat_interval = int(os.getenv("CHAT_HEARTBEAT_INTERVAL_SECONDS", "30"))
        protocol_version = os.getenv("CHAT_SSE_PROTOCOL_VERSION", "2025-11.v1")
        deprecate_partial_at = os.getenv("CHAT_SSE_PARTIAL_DEPRECATE_AT", "2026-03-01")

        # Validar tamanho da mensagem
        try:
            if message and len(message.encode("utf-8")) > max_bytes:
                _err = json.dumps(
                    {"error": "Message too large", "code": "MessageTooLarge"}, ensure_ascii=False
                )
                yield f"event: error\ndata: {_err}\n\n"
                return
        except Exception:
            pass

        conv = None
        try:
            conv = self._repo.get_conversation(conversation_id)
            self._validate_conversation_access(conversation_id, conv, user_id, project_id)
        except ChatRepositoryError:
            _err = json.dumps(
                {"error": "Conversation not found", "code": "ConversationNotFound"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {_err}\n\n"
            return
        except ChatServiceError as e:
            _err = json.dumps(
                {"error": str(e), "code": "AccessDenied"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {_err}\n\n"
            return

        start_t_overall = _time.time()
        start_t = start_t_overall  # Garantir que start_t está definida para o bloco de erro
        trace_id = uuid4().hex
        try:
            logger.info(
                "chat.stream", stage="start", conversation_id=conversation_id, trace_id=trace_id
            )
        except Exception:
            pass
        yield "event: start\n\n"
        _proto = json.dumps(
            {
                "version": protocol_version,
                "supports_partial": True,
                "deprecate_partial_at": deprecate_partial_at,
            },
            ensure_ascii=False,
        )
        yield f"event: protocol\ndata: {_proto}\n\n"
        # add user message
        self._repo.add_message(conversation_id, role="user", text=message)
        _ack = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
        yield f"event: ack\ndata: {_ack}\n\n"

        # compute prompt
        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)

        # RAG Logic
        relevant_memories = None
        if self._rag_service:
            relevant_memories = await self._rag_service.retrieve_context(
                message, user_id=user_id, conversation_id=conversation_id
            )

        prompt = await self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )
        in_tokens = self._prompt_service.estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)

        # Intercepta discovery interativo e responde sem invocar LLM
        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                _tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                yield f"event: token\ndata: {_tok}\n\n"
                # Compatibilidade temporária com clientes antigos
                yield f"event: partial\ndata: {_tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="discovery").observe(
                            ttft_ms / 1000.0
                        )
                        logger.info(
                            "chat.stream",
                            stage="ttft",
                            conversation_id=conversation_id,
                            trace_id=trace_id,
                            provider="janus",
                            model="discovery",
                            ttft_ms=ttft_ms,
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "discovery",
                "citations": [],
            }
            _, ui = self._split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            _done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {_done}\n\n"
            try:
                latency_ms = int((_time.time() - start_t_overall) * 1000)
                logger.info(
                    "chat.stream",
                    stage="done",
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    provider="janus",
                    model="discovery",
                    latency_ms=latency_ms,
                    retries=0,
                )
            except Exception:
                pass
            return

        # Intercepta geração automática de documentação das ferramentas em streaming
        if self._prompt_service.is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_tools_documentation(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                _tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                yield f"event: token\ndata: {_tok}\n\n"
                yield f"event: partial\ndata: {_tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="tools_docs").observe(
                            ttft_ms / 1000.0
                        )
                        logger.info(
                            "chat.stream",
                            stage="ttft",
                            conversation_id=conversation_id,
                            trace_id=trace_id,
                            provider="janus",
                            model="tools_docs",
                            ttft_ms=ttft_ms,
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "tools_docs",
                "citations": [],
            }
            _, ui = self._split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            _done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {_done}\n\n"
            return

        # Intercepta perguntas de capacidades e responde sem invocar LLM
        if self._prompt_service.is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_local_capabilities(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            # naive chunking for SSE partials
            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                _tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                # TTFT/timeout: se tempo até primeiro token exceder timeout, emitir erro
                ttft = _time.time() - start_t_overall
                limit = float(timeout_seconds or default_timeout)
                if limit > 0 and ttft > limit:
                    _err = json.dumps(
                        {"error": "TTFT timeout", "code": "TTFTTimeout"}, ensure_ascii=False
                    )
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                        CHAT_ERRORS_TOTAL.labels(code="TTFTTimeout").inc()
                        logger.error(
                            "chat.stream",
                            stage="error",
                            conversation_id=conversation_id,
                            trace_id=trace_id,
                            code="TTFTTimeout",
                        )
                    except Exception:
                        pass
                    yield f"event: error\ndata: {_err}\n\n"
                    return
                yield f"event: token\ndata: {_tok}\n\n"
                yield f"event: partial\ndata: {_tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="capabilities").observe(
                            ttft_ms / 1000.0
                        )
                        logger.info(
                            "chat.stream",
                            stage="ttft",
                            conversation_id=conversation_id,
                            trace_id=trace_id,
                            provider="janus",
                            model="capabilities",
                            ttft_ms=ttft_ms,
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "capabilities",
                "citations": [],
            }
            _, ui = self._split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            _done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {_done}\n\n"
            try:
                latency_ms = int((_time.time() - start_t_overall) * 1000)
                logger.info(
                    "chat.stream",
                    stage="done",
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    provider="janus",
                    model="capabilities",
                    latency_ms=latency_ms,
                    retries=0,
                )
            except Exception:
                pass
            return

        try:
            # Seleção antecipada de provider/modelo e CB early-block
            pre = self._llm.select_provider(
                role=role, priority=priority, user_id=user_id, project_id=project_id
            )
            current_provider = pre.get("provider")
            current_model = pre.get("model")
            if self._llm.is_provider_open(current_provider or ""):
                _err = json.dumps(
                    {"error": "Circuit open", "code": "CircuitOpen"}, ensure_ascii=False
                )
                try:
                    from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                    CHAT_ERRORS_TOTAL.labels(code="CircuitOpen").inc()
                    logger.error(
                        "chat.stream",
                        stage="error",
                        conversation_id=conversation_id,
                        trace_id=trace_id,
                        provider=current_provider,
                        model=current_model,
                        code="CircuitOpen",
                    )
                except Exception:
                    pass
                yield f"event: error\ndata: {_err}\n\n"
                return

            start_t = _time.time()
            # Executa LLM em thread e emite heartbeats enquanto aguarda
            task = asyncio.create_task(
                asyncio.to_thread(
                    self._llm.invoke_llm,
                    prompt=prompt,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
            )
            while not task.done():
                await asyncio.sleep(max(1, heartbeat_interval))
                hb = json.dumps({"timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                yield f"event: heartbeat\ndata: {hb}\n\n"
            result = await task
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            assistant_text = result.get("response", "")
            clean_text, ui = self._split_ui(assistant_text)
            current_provider = result.get("provider")
            if self._cb_should_block(current_provider):
                _err = json.dumps(
                    {"error": "Circuit open", "code": "CircuitOpen"}, ensure_ascii=False
                )
                try:
                    from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                    CHAT_ERRORS_TOTAL.labels(code="CircuitOpen").inc()
                    logger.error(
                        "chat.stream",
                        stage="error",
                        conversation_id=conversation_id,
                        trace_id=trace_id,
                        provider=current_provider,
                        code="CircuitOpen",
                    )
                except Exception:
                    pass
                yield f"event: error\ndata: {_err}\n\n"
                return
            # naive chunking for SSE partials
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                _tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                yield f"event: token\ndata: {_tok}\n\n"
                yield f"event: partial\ndata: {_tok}\n\n"
            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
            # custo aproximado
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

            # Disparar gatilhos pós-resposta
            try:
                self._trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass

            # Compute citations near the end based on user/session context
            citations: list[dict[str, Any]] = []
            try:
                from qdrant_client import models as _models

                from app.core.embeddings.embedding_manager import aembed_text
                from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client

                vec = await aembed_text(message)
                coll = (
                    await aget_or_create_collection(f"user_{user_id}")
                    if user_id
                    else await aget_or_create_collection("janus_episodic_memory")
                )

                must: list[_models.FieldCondition] = []
                if user_id:
                    must.append(
                        _models.FieldCondition(
                            key="metadata.user_id", match=_models.MatchValue(value=str(user_id))
                        )
                    )
                if conversation_id:
                    must.append(
                        _models.FieldCondition(
                            key="metadata.session_id",
                            match=_models.MatchValue(value=conversation_id),
                        )
                    )
                must_not: list[_models.FieldCondition] = [
                    _models.FieldCondition(
                        key="metadata.status", match=_models.MatchValue(value="duplicate")
                    )
                ]

                qfilter = (
                    _models.Filter(must=must, must_not=must_not)
                    if must
                    else _models.Filter(must_not=must_not)
                )
                client = get_async_qdrant_client()
                res = await client.query_points(
                    collection_name=coll,
                    query=vec,
                    limit=5,
                    with_payload=True,
                    query_filter=qfilter,
                )
                hits = getattr(res, "points", res) or []
                for h in hits:
                    payload = getattr(h, "payload", {}) or {}
                    meta = payload.get("metadata") or {}
                    citations.append(
                        {
                            "id": getattr(h, "id", None),
                            "doc_id": meta.get("doc_id"),
                            "file_path": meta.get("file_path"),
                            "type": meta.get("type"),
                            "origin": meta.get("origin"),
                            "score": float(getattr(h, "score", 0.0) or 0.0),
                        }
                    )
            except Exception:
                citations = []
            done_payload = {
                "conversation_id": conversation_id,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "citations": citations,
            }
            if ui:
                done_payload["ui"] = ui
            _done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {_done}\n\n"
            self._cb_on_success(current_provider)
            try:
                latency_ms = int((_time.time() - start_t_overall) * 1000)
                logger.info(
                    "chat.stream",
                    stage="done",
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    provider=result.get("provider"),
                    model=result.get("model"),
                    latency_ms=latency_ms,
                    retries=0,
                )
            except Exception:
                pass
        except Exception as e:
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(
                max(0.0, _time.time() - start_t)
            )
            _err = json.dumps({"error": str(e), "code": "InvocationError"}, ensure_ascii=False)
            try:
                from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                CHAT_ERRORS_TOTAL.labels(code="InvocationError").inc()
                logger.error(
                    "chat.stream",
                    stage="error",
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    provider=current_provider,
                    code="InvocationError",
                )
            except Exception:
                pass
            yield f"event: error\ndata: {_err}\n\n"
            try:
                self._cb_on_error(current_provider)
            except Exception:
                pass

    def _trigger_post_response_events(
        self,
        conversation_id: str,
        user_message: str,
        assistant_text: str,
        result: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        """Dispara tarefas assíncronas de consolidação e reflexion após uma resposta gerada."""
        # Consolidação de conhecimento (modo single)
        try:
            consolidation_payload = {
                "mode": "single",
                "experience_id": f"{conversation_id}:{int(_time.time())}",
                "experience_content": assistant_text,
                "metadata": {
                    "conversation_id": conversation_id,
                    "role": result.get("role"),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "user_message": (user_message or "")[:500],
                    "user_id": user_id,
                    "project_id": project_id,
                },
            }
            asyncio.create_task(
                publish_consolidation_task(consolidation_payload, correlation_id=conversation_id)
            )
        except Exception:
            pass

    # Circuit Breaker simples por provider
    def _cb_should_block(self, provider: str | None) -> bool:
        try:
            if not provider:
                return False
            state = getattr(self, "_cb_state", {})
            s = state.get(provider)
            if not s:
                return False
            opened_at = s.get("opened_at") or 0
            cooldown = int(os.getenv("CHAT_CB_COOLDOWN_SECONDS", "60"))
            if s.get("state") == "open" and (_time.time() - opened_at) < cooldown:
                return True
            return False
        except Exception:
            return False

    def _cb_on_error(self, provider: str | None) -> None:
        try:
            if not provider:
                return
            state = getattr(self, "_cb_state", {})
            s = state.get(provider) or {"failures": 0, "state": "closed"}
            s["failures"] = int(s.get("failures", 0)) + 1
            threshold = int(os.getenv("CHAT_CB_FAILURE_THRESHOLD", "5"))
            if s["failures"] >= threshold:
                s["state"] = "open"
                s["opened_at"] = _time.time()
                try:
                    from app.core.monitoring.chat_metrics import CHAT_CB_STATE_CHANGES

                    CHAT_CB_STATE_CHANGES.labels(provider=provider, state="open").inc()
                except Exception:
                    pass
            state[provider] = s
            self._cb_state = state
        except Exception:
            pass

    def _cb_on_success(self, provider: str | None) -> None:
        try:
            if not provider:
                return
            state = getattr(self, "_cb_state", {})
            s = state.get(provider) or {"failures": 0, "state": "closed"}
            s["failures"] = 0
            s["state"] = "closed"
            try:
                from app.core.monitoring.chat_metrics import CHAT_CB_STATE_CHANGES

                CHAT_CB_STATE_CHANGES.labels(provider=provider, state="closed").inc()
            except Exception:
                pass
            state[provider] = s
            self._cb_state = state
        except Exception:
            pass

    async def stream_events(self, conversation_id: str, user_id: str | None = None):
        """
        Streaming dedicado de eventos de agentes (background tasks) para esta conversa.
        Conecta no RabbitMQ e repassa eventos via SSE.
        """
        import json
        import time as _time

        from app.core.infrastructure.message_broker import get_broker

        yield "event: connected\ndata: {}\n\n"

        broker = await get_broker()
        queue = asyncio.Queue()

        async def on_event(payload):
            await queue.put(payload)

        # Routing key: janus.event.conversation.{cid}.#
        routing_key = f"janus.event.conversation.{conversation_id}.#"

        subscription_task = broker.start_subscription(
            exchange_name="janus.events",
            routing_key=routing_key,
            callback=on_event,
            queue_name="",  # Fila exclusiva
        )

        try:
            # Loop de consumo
            # Mantém conexão por X minutos ou até cliente desconectar
            # Timeout de 1h para long running tasks
            start_time = _time.time()
            max_duration = 3600

            while (_time.time() - start_time) < max_duration:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)

                    original_payload = payload
                    if isinstance(payload, (bytes, bytearray)):
                        try:
                            payload = json.loads(payload.decode("utf-8"))
                        except Exception:
                            payload = {
                                "content": original_payload.decode("utf-8", errors="replace")
                            }
                    elif isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            payload = {"content": payload}
                    elif not isinstance(payload, dict):
                        payload = {"content": str(payload)}

                    sse_event = {
                        "type": payload.get("event_type", "unknown"),
                        "agent": payload.get("agent_role", "unknown"),
                        "content": payload.get("content", ""),
                        "timestamp": payload.get("timestamp"),
                        "task_id": payload.get("task_id"),
                    }

                    yield f"event: agent_event\ndata: {json.dumps(sse_event, ensure_ascii=False)}\n\n"

                except TimeoutError:
                    # Heartbeat
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            # Cliente desconectou
            pass
        finally:
            subscription_task.cancel()
            try:
                await subscription_task
            except Exception:
                pass
            logger.info(f"Stream de eventos encerrado para {conversation_id}")


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service

    # --- Helpers ---
