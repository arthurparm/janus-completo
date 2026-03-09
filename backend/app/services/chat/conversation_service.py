import asyncio
from copy import deepcopy
from typing import Any

import structlog

from app.core.exceptions.chat_exceptions import ChatServiceError, ConversationNotFoundError
from app.core.monitoring.chat_metrics import update_active_conversations
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError

logger = structlog.get_logger(__name__)


class ConversationService:
    def __init__(self, repo: ChatRepository):
        self._repo = repo

    def _get_resolved_pending_statuses(self, messages: list[dict[str, Any]]) -> dict[int, str]:
        pending_action_ids: set[int] = set()
        for message in messages:
            confirmation = message.get("confirmation")
            if str(message.get("role")) != "assistant" or not isinstance(confirmation, dict):
                continue
            action_id = confirmation.get("pending_action_id")
            if isinstance(action_id, int):
                pending_action_ids.add(action_id)

        if not pending_action_ids:
            return {}

        try:
            from app.repositories.pending_action_repository import PendingActionRepository

            repo = PendingActionRepository()
            statuses: dict[int, str] = {}
            for action_id in pending_action_ids:
                item = repo.get(action_id)
                status = str(getattr(item, "status", "") or "").strip().lower()
                if status in {"approved", "rejected"}:
                    statuses[action_id] = status
            return statuses
        except Exception as e:
            logger.warning(
                "chat_history_pending_action_status_lookup_failed",
                error=str(e),
                pending_action_ids=sorted(pending_action_ids),
            )
            return {}

    def _reconcile_pending_confirmation_message(
        self,
        message: dict[str, Any],
        *,
        status_by_action_id: dict[int, str],
    ) -> dict[str, Any]:
        confirmation = message.get("confirmation")
        if str(message.get("role")) != "assistant" or not isinstance(confirmation, dict):
            return message
        action_id = confirmation.get("pending_action_id")
        if not isinstance(action_id, int):
            return message
        resolved_status = status_by_action_id.get(action_id)
        if resolved_status not in {"approved", "rejected"}:
            return message

        payload = deepcopy(message)
        payload_confirmation = dict(payload.get("confirmation") or {})
        payload_confirmation["required"] = False
        payload_confirmation["status"] = resolved_status
        payload_confirmation.pop("approve_endpoint", None)
        payload_confirmation.pop("reject_endpoint", None)
        payload["confirmation"] = payload_confirmation

        understanding = payload.get("understanding")
        if isinstance(understanding, dict):
            payload_understanding = dict(understanding)
            payload_understanding["requires_confirmation"] = False
            nested_confirmation = payload_understanding.get("confirmation")
            if isinstance(nested_confirmation, dict):
                resolved_nested = dict(nested_confirmation)
                resolved_nested["required"] = False
                resolved_nested["status"] = resolved_status
                resolved_nested.pop("approve_endpoint", None)
                resolved_nested.pop("reject_endpoint", None)
                payload_understanding["confirmation"] = resolved_nested
            payload["understanding"] = payload_understanding

        agent_state = payload.get("agent_state")
        resolved_agent_state = dict(agent_state) if isinstance(agent_state, dict) else {}
        resolved_agent_state["state"] = "completed"
        resolved_agent_state["requires_confirmation"] = False
        resolved_agent_state["reason"] = resolved_status
        payload["agent_state"] = resolved_agent_state
        return payload

    def _reconcile_pending_confirmation_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        status_by_action_id = self._get_resolved_pending_statuses(messages)
        if not status_by_action_id:
            return messages
        return [
            self._reconcile_pending_confirmation_message(
                message,
                status_by_action_id=status_by_action_id,
            )
            for message in messages
        ]

    def validate_conversation_access(
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

    def start_conversation(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        cid = self._repo.start_conversation(persona, user_id, project_id)
        try:
            count = self._repo.count_conversations()
            update_active_conversations(count)
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to update active conversation metrics: {e}")
        return cid

    async def start_conversation_async(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        return await asyncio.to_thread(self.start_conversation, persona, user_id, project_id)

    def get_history(
        self,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        logger.info("log_info", message=f"Getting chat history for conversation: {conversation_id}")
        try:
            conv = self._repo.get_conversation(conversation_id)
            self.validate_conversation_access(conversation_id, conv, user_id, project_id)

            if not isinstance(conv, dict):
                logger.error("log_error", message=f"Invalid conversation structure for {conversation_id}: expected dict, got {type(conv)}"
                )
                raise ConversationNotFoundError(
                    f"Invalid conversation structure for {conversation_id}"
                )

            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                logger.warning("log_warning", message=f"Messages is not a list for conversation {conversation_id}, converting to empty list"
                )
                messages = []
            messages = self._reconcile_pending_confirmation_messages(messages)

            logger.info("log_info", message=f"Successfully retrieved conversation {conversation_id} with {len(messages)} messages"
            )

            return {
                "conversation_id": conversation_id,
                "persona": conv.get("persona"),
                "messages": messages,
            }
        except ChatRepositoryError as e:
            logger.error("log_error", message=f"Repository error getting conversation {conversation_id}: {e}")
            raise ConversationNotFoundError(str(e)) from e
        except ConversationNotFoundError:
            raise
        except ChatServiceError:
            raise
        except Exception as e:
            if "conversation not found" in str(e).lower():
                raise ConversationNotFoundError(str(e)) from e
            logger.error("log_error", message=f"Unexpected error getting history for conversation {conversation_id}: {e}",
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
        logger.info("log_info", message=f"Getting paginated chat history for conversation: {conversation_id}, limit: {limit}, offset: {offset}"
        )

        try:
            limit = min(limit, 200)
            conv = self._repo.get_conversation(conversation_id)

            if not isinstance(conv, dict):
                logger.error("log_error", message=f"Invalid conversation structure for {conversation_id}: expected dict, got {type(conv)}"
                )
                raise ConversationNotFoundError(
                    f"Invalid conversation structure for {conversation_id}"
                )

            self.validate_conversation_access(conversation_id, conv, user_id, project_id)

            result = self._repo.get_history_paginated(
                conversation_id, limit=limit, offset=offset, before_ts=before_ts, after_ts=after_ts
            )

            logger.info("log_info", message=f"Successfully retrieved paginated history for conversation {conversation_id}: "
                f"{len(result['messages'])} messages (total: {result['total_count']})"
            )

            return {
                "conversation_id": conversation_id,
                "persona": conv.get("persona"),
                "messages": self._reconcile_pending_confirmation_messages(result["messages"]),
                "total_count": result["total_count"],
                "has_more": result["has_more"],
                "next_offset": result["next_offset"],
                "limit": result["limit"],
                "offset": result["offset"],
            }
        except ChatRepositoryError as e:
            logger.error("log_error", message=f"Repository error getting paginated history for {conversation_id}: {e}")
            raise ConversationNotFoundError(str(e)) from e
        except ConversationNotFoundError:
            raise
        except ChatServiceError:
            raise
        except Exception as e:
            if "conversation not found" in str(e).lower():
                raise ConversationNotFoundError(str(e)) from e
            logger.error("log_error", message=f"Unexpected error getting paginated history for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            raise ChatServiceError(
                f"Failed to get paginated history for conversation {conversation_id}: {e!s}"
            )

    async def list_conversations(
        self, user_id: str | None = None, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._repo.list_conversations, user_id=user_id, project_id=project_id, limit=limit
        )

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
            raise ChatServiceError(str(e)) from e

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
            raise ChatServiceError(str(e)) from e

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
            raise ChatServiceError(str(e)) from e

    async def delete_message(
        self, conversation_id: str, message_id: int, user_id: str | None = None
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.delete_message, conversation_id, message_id, user_id=user_id
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e)) from e

    async def replace_last_assistant_message(
        self, conversation_id: str, new_text: str, user_id: str | None = None
    ) -> None:
        try:
            await asyncio.to_thread(
                self._repo.replace_last_assistant_message,
                conversation_id,
                new_text,
                user_id,
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e)) from e

    async def get_last_assistant_message(
        self, conversation_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(
                self._repo.get_last_assistant_message,
                conversation_id,
                user_id,
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e)) from e

    async def update_message_payload(
        self,
        conversation_id: str,
        message_id: int,
        patch: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(
                self._repo.update_message_payload,
                conversation_id,
                message_id,
                patch,
                user_id,
            )
        except ChatRepositoryError as e:
            raise ChatServiceError(str(e)) from e
