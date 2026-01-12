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
from app.core.workers.async_consolidation_worker import publish_consolidation_task
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.memory_service import MemoryService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.tool_executor_service import ToolExecutorService
from app.services.tool_service import ToolService

logger = structlog.get_logger(__name__)


class ChatServiceError(Exception):
    """Base exception for Chat service errors."""

    pass


class ConversationNotFoundError(ChatServiceError):
    pass


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
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._memory = memory_service

        # New services injection
        self._prompt_service = prompt_service or PromptBuilderService()
        self._tool_executor = tool_executor_service or ToolExecutorService()

        # RAGService setup
        if rag_service:
            self._rag_service = rag_service
        elif memory_service:
             self._rag_service = RAGService(repo, llm_service, memory_service)
        else:
             self._rag_service = None

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

    async def _publish_agent_event(
        self,
        conversation_id: str,
        event_type: str,
        agent_role: str,
        content: str,
        task_id: str | None = None
    ):
        """Publish agent event to RabbitMQ for SSE streaming to frontend."""
        try:
            broker = await get_broker()
            routing_key = f"janus.event.conversation.{conversation_id}.{event_type}"
            payload = {
                "conversation_id": conversation_id,
                "event_type": event_type,
                "agent_role": agent_role,
                "content": content,
                "timestamp": _time.time(),
                "task_id": task_id or conversation_id
            }
            await broker.publish_to_exchange(
                exchange_name="janus.events",
                routing_key=routing_key,
                message=payload
            )
        except Exception as e:
            # Don't break agent execution if event publishing fails
            logger.warning(f"Failed to publish agent event: {e}", conversation_id=conversation_id)

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

        persona = conv.get("persona") or "assistant"
        history = await asyncio.to_thread(self._repo.get_recent_messages, conversation_id, limit=60)
        # RAG Logic
        relevant_memories = None
        if self._rag_service:
             relevant_memories = await self._rag_service.retrieve_context(message)

        prompt = self._prompt_service.build_prompt(persona, history, message, conv.get("summary"), relevant_memories)

        # Store user message before invocation
        await asyncio.to_thread(self._repo.add_message, conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        in_tokens = self._prompt_service.estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)
        try:
            if self._rag_service:
                await self._rag_service.maybe_index_message(text=message, user_id=user_id, conversation_id=conversation_id, role="user")
        except Exception as e:
            logger.warning(f"Failed to index user message for {conversation_id}: {e}")

        # Quick Commands (Quick Win) - Comandos com / são processados diretamente
        if self._is_quick_command(message):
            start_t = _time.time()
            assistant_text = self._handle_quick_command(message, conversation_id, user_id)
            if assistant_text:
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
                    "response": assistant_text,
                    "provider": "janus",
                    "model": "quick_command",
                    "role": role.value,
                    "conversation_id": conversation_id,
                }
                return result

        # Intercepta fluxo de descoberta interativa de ferramentas/configuração
        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
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
                "response": assistant_text,
                "provider": "janus",
                "model": "discovery",
                "role": role.value,
            }

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
                "response": assistant_text,
                "provider": "janus",
                "model": "tools_docs",
                "role": role.value,
            }

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
                "response": assistant_text,
                "provider": "janus",
                "model": "capabilities",
                "role": role.value,
            }

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

        try:
            start_t = _time.time()
            result = await self._run_agent_loop(
                conversation_id=conversation_id,
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
        await asyncio.to_thread(
            self._repo.add_message, conversation_id, role="assistant", text=assistant_text
        )
        out_tokens = self._prompt_service.estimate_tokens(assistant_text)
        CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
        try:
            if self._rag_service:
                await self._rag_service.maybe_index_message(
                    text=assistant_text,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="assistant",
                )
        except Exception:
            pass

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
            # não quebrar o fluxo de resposta por erro de sumarização
            pass

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

    async def _run_agent_loop(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None,
        user_id: str | None,
        project_id: str | None,
        max_iterations: int = 5,  # Reduzido: fix de research paralysis torna valores altos desnecessários
    ) -> dict[str, Any]:
        """
        Executa o loop ReAct (Reasoning + Acting).
        Permite que o modelo chame ferramentas sequencialmente até chegar a uma resposta final.
        """
        try:
            conv = await asyncio.to_thread(self._repo.get_conversation, conversation_id)
        except ChatRepositoryError as e:
            raise ConversationNotFoundError(str(e)) from e

        persona = conv.get("persona") or "assistant"

        # Histórico inicial
        history = await asyncio.to_thread(self._repo.get_recent_messages, conversation_id, limit=20)

        # RAG: Retrieve relevant memories/documents BEFORE building prompt
        relevant_memories = None
        if self._rag_service:
             relevant_memories = await self._rag_service.retrieve_context(message)

        # Prompt inicial (now with memories)
        current_prompt = self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )

        # Tokens de entrada (aproximado)
        total_in_tokens = self._estimate_tokens(current_prompt)
        total_out_tokens = 0
        final_response_text = ""
        last_result = {}

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(
                f"Agent loop iteration {iteration}/{max_iterations} for conversation {conversation_id}"
            )

            # Publish thought event
            await self._publish_agent_event(
                conversation_id=conversation_id,
                event_type="agent_thought",
                agent_role=role.value,
                content=f"Iteration {iteration}/{max_iterations}: Analyzing request and planning response"
            )

            # Invocar LLM
            try:
                result = await asyncio.to_thread(
                    self._llm.invoke_llm,
                    prompt=current_prompt,
                    role=role,
                    priority=priority,
                    timeout_seconds=timeout_seconds,
                    user_id=user_id,
                    project_id=project_id,
                )
                last_result = result
            except LLMServiceError as e:
                logger.error("LLM invocation failed in agent loop", exc_info=e)
                if iteration == 1:
                    raise ChatServiceError(str(e)) from e
                break  # Se falhar no meio, retornamos o que temos

            response_text = result.get("response", "")
            total_out_tokens += self._estimate_tokens(response_text)

            # Verificar chamada de ferramenta
            tool_calls = self._tool_executor.parse_tool_calls(response_text)

            if not tool_calls:
                # Resposta final (sem ferramentas)
                final_response_text = response_text

                # Publish decision event
                await self._publish_agent_event(
                    conversation_id=conversation_id,
                    event_type="decision",
                    agent_role=role.value,
                    content="Finalizing response - all analysis complete"
                )
                break

            # Se houver ferramentas, executamos
            logger.info(f"Detected {len(tool_calls)} tool calls in iteration {iteration}")

            # Publish tool call events
            for tool_call in tool_calls:
                await self._publish_agent_event(
                    conversation_id=conversation_id,
                    event_type="tool_call",
                    agent_role=role.value,
                    content=f"Calling tool: {tool_call.get('name', 'unknown')}"
                )

            # Adiciona o pensamento do agente ao prompt (Acting)
            current_prompt += f"\nAssistant: {response_text}"

            # Executa ferramentas
            tool_outputs = await self._tool_executor.execute_tool_calls(tool_calls)

            # Adiciona resultados ao prompt (Observation)
            for output in tool_outputs:
                current_prompt += f"\nSystem: Tool Output ({output['name']}):\n{output['result']}"

                # Publish tool completion event
                result_preview = str(output['result'])[:200] + ("..." if len(str(output['result'])) > 200 else "")
                await self._publish_agent_event(
                    conversation_id=conversation_id,
                    event_type="tool_end",
                    agent_role=role.value,
                    content=f"Tool {output['name']} completed: {result_preview}"
                )

            # Continua para a próxima iteração (Reasoning)

        if not final_response_text and iteration >= max_iterations:
            # Log para debugging
            logger.warning(
                f"Agent reached max iterations ({max_iterations}) for conversation {conversation_id}. "
                f"Message: {message[:100]}"
            )

            # Mensagem útil ao usuário
            final_response_text = (
                f"Desculpe, essa tarefa mostrou-se mais complexa do que esperado. "
                f"Tentei {iteration} passos mas ainda não consegui uma resposta completa.\n\n"
                f"**Sugestões:**\n"
                f"- Simplifique a pergunta\n"
                f"- Quebre em partes menores\n"
                f"- Seja mais específico sobre o que precisa\n\n"
                f"*Estou sempre aprendendo a ser mais eficiente!* 🤖"
            )
            # Use last result metadata if available

        return {
            "response": final_response_text,
            "provider": last_result.get("provider", "janus"),
            "model": last_result.get("model", "agent"),
            "role": role.value,
            "conversation_id": conversation_id,
            "total_in_tokens": total_in_tokens,
            "total_out_tokens": total_out_tokens,
        }







    def get_history(self, conversation_id: str) -> dict[str, Any]:
        logger.info(f"Getting chat history for conversation: {conversation_id}")
        try:
            conv = self._repo.get_conversation(conversation_id)

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

            # Validar acesso (RBAC)
            if user_id and conv.get("user_id") and conv["user_id"] != user_id:
                logger.warning(
                    f"User {user_id} attempted to access conversation {conversation_id} owned by {conv['user_id']}"
                )
                raise ChatServiceError("Access denied: user_id mismatch")

            if project_id and conv.get("project_id") and conv["project_id"] != project_id:
                logger.warning(
                    f"Project mismatch for conversation {conversation_id}: expected {conv['project_id']}, got {project_id}"
                )
                raise ChatServiceError("Access denied: project_id mismatch")

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


    # --- Quick Commands System (Quick Win) ---
    QUICK_COMMANDS = {
        "/help": "_handle_help_command",
        "/status": "_handle_status_command",
        "/memory": "_handle_memory_command",
        "/tools": "_handle_tools_command",
        "/feedback": "_handle_feedback_command",
        "/about": "_handle_about_command",
    }

    def _is_quick_command(self, text: str) -> bool:
        """Detecta se a mensagem é um comando rápido."""
        if not text:
            return False
        t = text.strip().lower()
        return any(t.startswith(cmd) for cmd in self.QUICK_COMMANDS.keys())

    def _handle_quick_command(
        self, text: str, conversation_id: str, user_id: str | None = None
    ) -> str | None:
        """Processa um comando rápido e retorna a resposta."""
        if not text:
            return None
        t = text.strip().lower()

        for cmd, handler_name in self.QUICK_COMMANDS.items():
            if t.startswith(cmd):
                handler = getattr(self, handler_name, None)
                if handler:
                    args = t[len(cmd) :].strip()
                    return handler(args, conversation_id, user_id)
        return None

    def _handle_help_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /help."""
        return """## 🤖 JANUS — Comandos Rápidos

**Navegação:**
- `/help` — Exibe esta mensagem de ajuda
- `/about` — Informações sobre o JANUS
- `/status` — Status do sistema e componentes

**Ferramentas:**
- `/tools` — Lista ferramentas disponíveis
- `/memory` — Informações sobre memória e contexto

**Feedback:**
- `/feedback` — Como enviar feedback sobre respostas

**Dicas:**
- Você pode me perguntar qualquer coisa naturalmente
- Use "quais são suas capacidades" para ver funcionalidades
- Peça "documentação de ferramentas" para detalhes técnicos

*À sua disposição!* ✨"""

    def _handle_status_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /status."""
        try:
            from app.core.monitoring.health_monitor import get_health_monitor

            monitor = get_health_monitor()
            if monitor:
                health_status = monitor.get_status()

                components_status = []
                for comp, status in health_status.get("components", {}).items():
                    emoji = "✅" if status.get("healthy", False) else "❌"
                    components_status.append(
                        f"- {emoji} **{comp}**: {status.get('status', 'unknown')}"
                    )

                components_text = (
                    "\n".join(components_status)
                    if components_status
                    else "- Nenhum componente monitorado"
                )

                return f"""## 📊 Status do Sistema

**Saúde Geral:** {"✅ Saudável" if health_status.get("healthy", False) else "⚠️ Atenção"}
**Uptime:** {health_status.get("uptime", "N/A")}

### Componentes:
{components_text}

### Métricas Rápidas:
- **Conversas ativas:** {health_status.get("active_conversations", "N/A")}
- **Latência média:** {health_status.get("avg_latency_ms", "N/A")}ms

*Use `/help` para ver outros comandos.*"""
            else:
                return "⚠️ Monitor de saúde não disponível. Use `/help` para outros comandos."
        except Exception as e:
            logger.warning(f"Erro ao obter status: {e}")
            return """## 📊 Status do Sistema

**Status:** ✅ Operacional
**Versão:** 1.0.0

*Sistema respondendo normalmente. Use `/help` para ver comandos disponíveis.*"""

    def _handle_memory_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /memory."""
        try:
            if self._memory:
                stats = self._memory.get_stats() if hasattr(self._memory, "get_stats") else {}
                return f"""## 🧠 Memória e Contexto

**Conversa Atual:** `{conversation_id[:8]}...`
**Usuário:** {user_id or "Anônimo"}

### Memória Semântica:
- **Experiências armazenadas:** {stats.get("total_experiences", "N/A")}
- **Cache de curto prazo:** {stats.get("short_term_cache_size", "N/A")} itens

### Contexto da Conversa:
- Histórico mantido para personalização
- Consolidação de conhecimento ativa

*Dica: Eu lembro de conversas anteriores para personalizar respostas!*"""
            else:
                return (
                    """## 🧠 Memória e Contexto

**Conversa Atual:** `"""
                    + conversation_id[:8]
                    + """...`

*Serviço de memória em modo básico. Histórico de conversa mantido.*"""
                )
        except Exception as e:
            logger.warning(f"Erro ao obter info de memória: {e}")
            return "⚠️ Informações de memória temporariamente indisponíveis."

    def _handle_tools_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /tools."""
        if self._tools:
            try:
                metas = self._tools.list_tools(category=None, permission_level=None, tags=None)
                if metas:
                    tools_list = []
                    for m in metas[:10]:  # Limitar a 10 ferramentas
                        cat = getattr(m.category, "value", str(m.category))
                        tools_list.append(f"- **{m.name}** ({cat})")

                    tools_text = "\n".join(tools_list)
                    more_text = (
                        f"\n\n*...e mais {len(metas) - 10} ferramentas*" if len(metas) > 10 else ""
                    )

                    return f"""## 🔧 Ferramentas Disponíveis

**Total:** {len(metas)} ferramentas registradas

### Principais:
{tools_text}{more_text}

*Peça "documentação de ferramentas" para detalhes completos.*"""
                else:
                    return "## 🔧 Ferramentas\n\nNenhuma ferramenta registrada no momento."
            except Exception as e:
                logger.warning(f"Erro ao listar ferramentas: {e}")
                return "⚠️ Erro ao listar ferramentas. Tente novamente."
        else:
            return "## 🔧 Ferramentas\n\nServiço de ferramentas não disponível."

    def _handle_feedback_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /feedback."""
        return """## 💬 Como Enviar Feedback

Seu feedback me ajuda a melhorar! Há três formas de contribuir:

### 👍 Thumbs Up / 👎 Thumbs Down
Use os botões de feedback após cada resposta minha para indicar se foi útil.

### 📝 Comentários
Ao dar feedback, você pode adicionar um comentário explicando o que funcionou ou não.

### 🔗 API de Feedback
Para integrações: `POST /api/v1/feedback/thumbs-up` ou `/thumbs-down`

### Métricas
Seu feedback é usado para:
- Melhorar a qualidade das respostas
- Identificar áreas problemáticas
- Otimizar modelos e prompts

*Obrigado por ajudar a me tornar melhor!* 🙏"""

    def _handle_about_command(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Responde ao comando /about."""
        from app.config import settings

        return f"""## 🤖 Sobre o JANUS

**JANUS AI Architect** — Assistente de IA Avançado

### Versão
- **Backend:** {settings.APP_VERSION}
- **Ambiente:** {settings.ENVIRONMENT}

### Capacidades Principais
- 💬 **Conversação inteligente** com memória de longo prazo
- 🔧 **Ferramentas dinâmicas** para automação e produtividade
- 🧠 **Memória semântica** com Qdrant + Neo4j
- 📊 **Observabilidade completa** com Prometheus/Grafana
- 🔄 **Multi-agentes** para tarefas complexas

### Inspiração
Inspirado no J.A.R.V.I.S. — Just A Rather Very Intelligent System

*"À sua disposição, senhor."* ✨"""



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
        conv = self._repo.get_conversation(conversation_id)
        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)

        # RAG Logic
        relevant_memories = None
        if self._rag_service:
             relevant_memories = await self._rag_service.retrieve_context(message)

        prompt = self._prompt_service.build_prompt(persona, history, message, conv.get("summary"), relevant_memories)
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

            _done = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "provider": "janus",
                    "model": "discovery",
                    "citations": [],
                }
            )
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

            _done = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "provider": "janus",
                    "model": "tools_docs",
                    "citations": [],
                }
            )
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

            _done = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "provider": "janus",
                    "model": "capabilities",
                    "citations": [],
                }
            )
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
                hits = await client.search(
                    collection_name=coll,
                    query_vector=vec,
                    limit=5,
                    with_payload=True,
                    query_filter=qfilter,
                )
                for h in hits or []:
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
            _done = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "citations": citations,
                },
                ensure_ascii=False,
            )
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
                            payload = {"content": original_payload.decode("utf-8", errors="replace")}
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
