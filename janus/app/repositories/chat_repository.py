from time import time
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class ChatRepositoryError(Exception):
    """Base exception for Chat repository errors."""

    pass


class ChatRepository:
    """
    Repository with durable file persistence for chat conversations and messages.
    Structure:
    {
        conversation_id: {
            "persona": Optional[str],
            "user_id": Optional[str],
            "project_id": Optional[str],
            "title": str,
            "created_at": float,
            "updated_at": float,
            "summary": Optional[str],
            "messages": [
                {"timestamp": float, "role": str, "text": str}
            ]
        }
    }
    """

    def __init__(self, store_path: str = "data/chat_store.json"):
        self._conversations: dict[str, dict[str, Any]] = {}
        self._store_path = store_path
        self._ensure_store_dir()
        self._load()

    def _ensure_store_dir(self) -> None:
        import os

        d = os.path.dirname(self._store_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load(self) -> None:
        import json
        import os

        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._conversations = data
            except Exception:
                self._conversations = {}

    def _save(self) -> None:
        import json

        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._conversations, f, ensure_ascii=False, indent=2)

    def start_conversation(
        self,
        persona: str | None,
        user_id: str | None,
        project_id: str | None,
        title: str | None = None,
    ) -> str:
        conversation_id = f"c_{uuid4().hex}"
        logger.info(
            "Starting new conversation",
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
        )
        now = time()
        self._conversations[conversation_id] = {
            "persona": persona,
            "user_id": user_id,
            "project_id": project_id,
            "title": title or "Nova Conversa",
            "created_at": now,
            "updated_at": now,
            "summary": None,
            "messages": [],
        }
        self._save()
        return conversation_id

    def add_message(self, conversation_id: str, role: str, text: str) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        conv["messages"].append({"timestamp": time(), "role": role, "text": text})
        conv["updated_at"] = time()
        self._save()

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        return conv

    def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        logger.info(f"Getting history for conversation: {conversation_id}")
        try:
            conv = self.get_conversation(conversation_id)
            messages = conv.get("messages", [])

            if not isinstance(messages, list):
                logger.error(
                    f"Invalid messages structure for conversation {conversation_id}: expected list, got {type(messages)}"
                )
                return []

            # Validar estrutura das mensagens
            valid_messages = []
            for i, msg in enumerate(messages):
                if isinstance(msg, dict) and "timestamp" in msg and "role" in msg and "text" in msg:
                    valid_messages.append(msg)
                else:
                    logger.warning(
                        f"Invalid message structure at index {i} in conversation {conversation_id}: {msg}"
                    )

            logger.info(
                f"Returning {len(valid_messages)} valid messages from {len(messages)} total for conversation {conversation_id}"
            )
            return valid_messages

        except Exception as e:
            logger.error(
                f"Error getting history for conversation {conversation_id}: {e}", exc_info=True
            )
            raise

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        messages = self.get_history(conversation_id)
        return messages[-limit:] if limit > 0 else messages

    def list_conversations(
        self, user_id: str | None = None, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for cid, conv in self._conversations.items():
            if user_id and conv.get("user_id") != user_id:
                continue
            if project_id and conv.get("project_id") != project_id:
                continue
            items.append(
                {
                    "conversation_id": cid,
                    "title": conv.get("title"),
                    "created_at": conv.get("created_at"),
                    "updated_at": conv.get("updated_at"),
                    "last_message": (
                        (conv.get("messages") or [])[-1] if conv.get("messages") else None
                    ),
                }
            )
        items.sort(key=lambda x: x.get("updated_at") or 0, reverse=True)
        return items[:limit]

    def rename_conversation(
        self,
        conversation_id: str,
        new_title: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        if user_id and conv.get("user_id") != user_id:
            raise ChatRepositoryError("Access denied: user_id mismatch")
        if project_id and conv.get("project_id") != project_id:
            raise ChatRepositoryError("Access denied: project_id mismatch")
        conv["title"] = new_title
        conv["updated_at"] = time()
        self._save()

    def delete_conversation(
        self, conversation_id: str, user_id: str | None = None, project_id: str | None = None
    ) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        if user_id and conv.get("user_id") != user_id:
            raise ChatRepositoryError("Access denied: user_id mismatch")
        if project_id and conv.get("project_id") != project_id:
            raise ChatRepositoryError("Access denied: project_id mismatch")
        del self._conversations[conversation_id]
        self._save()

    def update_summary(self, conversation_id: str, summary: str | None) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        conv["summary"] = summary
        conv["updated_at"] = time()
        self._save()

    def count_conversations(self) -> int:
        return len(self._conversations)
