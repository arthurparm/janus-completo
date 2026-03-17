from typing import Any

from fastapi import Request

from app.core.exceptions.chat_exceptions import (
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
)
from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_repository import ChatRepository
from app.services.chat import ConversationService, MessageOrchestrationService, StreamingService
from app.services.chat.message_helpers import (
    attach_understanding as helper_attach_understanding,
    build_understanding_payload as helper_build_understanding_payload,
    estimate_tokens as helper_estimate_tokens,
    format_tool_creation_response as helper_format_tool_creation_response,
    is_explicit_tool_creation as helper_is_explicit_tool_creation,
    split_ui as helper_split_ui,
)
from app.services.chat_agent_loop import ChatAgentLoop
from app.services.chat_command_handler import ChatCommandHandler
from app.services.chat_event_publisher import ChatEventPublisher
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.outbox_service import OutboxService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.tool_executor_service import ToolExecutorService
from app.services.tool_service import ToolService


class ChatService:
    """
    Stable facade for chat operations.
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
        outbox_service: OutboxService | None = None,
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._memory = memory_service
        self._outbox_service = outbox_service
        # Public aliases preserved for test utilities/introspection helpers.
        self.repo = repo
        self.llm_service = llm_service

        self._prompt_service = prompt_service or PromptBuilderService()
        self._tool_executor = tool_executor_service or ToolExecutorService()
        if rag_service:
            self._rag_service = rag_service
        elif memory_service:
            self._rag_service = RAGService(repo, llm_service, memory_service)
        else:
            self._rag_service = None

        self._command_handler = ChatCommandHandler(tool_service, memory_service)
        self._event_publisher = ChatEventPublisher(db_logger=event_logger)
        self._agent_loop = ChatAgentLoop(
            llm_service=llm_service,
            tool_executor=self._tool_executor,
            rag_service=self._rag_service,
            event_publisher=self._event_publisher,
            prompt_service=self._prompt_service,
        )
        self._conversation_service = ConversationService(repo)
        self._message_orchestration_service = MessageOrchestrationService(
            repo=repo,
            llm_service=llm_service,
            tool_service=tool_service,
            prompt_service=self._prompt_service,
            rag_service=self._rag_service,
            command_handler=self._command_handler,
            agent_loop=self._agent_loop,
            conversation_service=self._conversation_service,
            outbox_service=outbox_service,
        )
        self._streaming_service = StreamingService(
            repo=repo,
            llm_service=llm_service,
            tool_service=tool_service,
            prompt_service=self._prompt_service,
            rag_service=self._rag_service,
            conversation_service=self._conversation_service,
            message_orchestration_service=self._message_orchestration_service,
        )

    def _estimate_tokens(self, text: str) -> int:
        return helper_estimate_tokens(self._prompt_service, text)

    def _split_ui(self, text: str) -> tuple[str, dict[str, Any] | None]:
        return helper_split_ui(text)

    def _build_understanding_payload(self, message: str) -> dict[str, Any] | None:
        return helper_build_understanding_payload(message)

    def _attach_understanding(
        self,
        payload: dict[str, Any],
        understanding: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return helper_attach_understanding(payload, understanding)

    def _is_explicit_tool_creation(self, message: str) -> bool:
        return helper_is_explicit_tool_creation(message)

    def _format_tool_creation_response(self, result: dict[str, Any]) -> str:
        return helper_format_tool_creation_response(result)

    def _validate_conversation_access(
        self,
        conversation_id: str,
        conv: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        self._conversation_service.validate_conversation_access(
            conversation_id, conv, user_id, project_id
        )

    def _trigger_post_response_events(
        self,
        conversation_id: str,
        user_message: str,
        assistant_text: str,
        result: dict[str, Any],
        user_id: str | None,
        project_id: str | None,
    ) -> None:
        self._message_orchestration_service.trigger_post_response_events(
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_text=assistant_text,
            result=result,
            user_id=user_id,
            project_id=project_id,
        )

    def start_conversation(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        return self._conversation_service.start_conversation(persona, user_id, project_id)

    async def start_conversation_async(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        return await self._conversation_service.start_conversation_async(persona, user_id, project_id)

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole,
        priority: ModelPriority,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        knowledge_space_id: str | None = None,
        identity_source: str = "unknown",
    ) -> dict[str, Any]:
        return await self._message_orchestration_service.send_message(
            conversation_id=conversation_id,
            message=message,
            role=role,
            priority=priority,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            knowledge_space_id=knowledge_space_id,
            identity_source=identity_source,
        )

    def get_history(
        self,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return self._conversation_service.get_history(
            conversation_id=conversation_id, user_id=user_id, project_id=project_id
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
        return self._conversation_service.get_history_paginated(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            before_ts=before_ts,
            after_ts=after_ts,
            user_id=user_id,
            project_id=project_id,
        )

    async def list_conversations(
        self, user_id: str | None = None, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await self._conversation_service.list_conversations(
            user_id=user_id, project_id=project_id, limit=limit
        )

    async def rename_conversation(
        self,
        conversation_id: str,
        new_title: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        await self._conversation_service.rename_conversation(
            conversation_id=conversation_id,
            new_title=new_title,
            user_id=user_id,
            project_id=project_id,
        )

    async def delete_conversation(
        self, conversation_id: str, user_id: str | None = None, project_id: str | None = None
    ) -> None:
        await self._conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
        )

    async def update_message(
        self, conversation_id: str, message_id: int, new_text: str, user_id: str | None = None
    ) -> None:
        await self._conversation_service.update_message(
            conversation_id=conversation_id,
            message_id=message_id,
            new_text=new_text,
            user_id=user_id,
        )

    async def delete_message(
        self, conversation_id: str, message_id: int, user_id: str | None = None
    ) -> None:
        await self._conversation_service.delete_message(
            conversation_id=conversation_id, message_id=message_id, user_id=user_id
        )

    async def replace_last_assistant_message(
        self, conversation_id: str, new_text: str, user_id: str | None = None
    ) -> None:
        await self._conversation_service.replace_last_assistant_message(
            conversation_id=conversation_id,
            new_text=new_text,
            user_id=user_id,
        )

    async def get_last_assistant_message(
        self, conversation_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        return await self._conversation_service.get_last_assistant_message(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    async def update_message_payload(
        self,
        conversation_id: str,
        message_id: int,
        patch: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._conversation_service.update_message_payload(
            conversation_id=conversation_id,
            message_id=message_id,
            patch=patch,
            user_id=user_id,
        )

    async def stream_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole | None = None,
        priority: ModelPriority | None = None,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        knowledge_space_id: str | None = None,
        identity_source: str = "unknown",
        requested_role: str | None = None,
        routing_decision: Any | None = None,
        route_applied: bool | None = None,
    ):
        async for chunk in self._streaming_service.stream_message(
            conversation_id=conversation_id,
            message=message,
            role=role,
            priority=priority,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            knowledge_space_id=knowledge_space_id,
            identity_source=identity_source,
            requested_role=requested_role,
            routing_decision=routing_decision,
            route_applied=route_applied,
        ):
            yield chunk

    async def stream_events(self, conversation_id: str, user_id: str | None = None):
        async for chunk in self._streaming_service.stream_events(
            conversation_id=conversation_id,
            user_id=user_id,
        ):
            yield chunk


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
