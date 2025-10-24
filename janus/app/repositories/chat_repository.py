import structlog
from typing import Dict, Any, List, Optional
from uuid import uuid4
from time import time

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
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._store_path = store_path
        self._ensure_store_dir()
        self._load()

    def _ensure_store_dir(self) -> None:
        import os
        d = os.path.dirname(self._store_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load(self) -> None:
        import os, json
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._conversations = data
            except Exception:
                self._conversations = {}

    def _save(self) -> None:
        import json
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._conversations, f, ensure_ascii=False, indent=2)

    def start_conversation(self, persona: Optional[str], user_id: Optional[str], project_id: Optional[str],
                           title: Optional[str] = None) -> str:
        conversation_id = f"c_{uuid4().hex}"
        logger.info("Starting new conversation", conversation_id=conversation_id, user_id=user_id,
                    project_id=project_id)
        now = time()
        self._conversations[conversation_id] = {
            "persona": persona,
            "user_id": user_id,
            "project_id": project_id,
            "title": title or "Nova Conversa",
            "created_at": now,
            "updated_at": now,
            "summary": None,
            "messages": []
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

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        return conv

    def get_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        return list(self.get_conversation(conversation_id)["messages"])

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        messages = self.get_history(conversation_id)
        return messages[-limit:] if limit > 0 else messages

    def list_conversations(self, user_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50) -> \
    List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for cid, conv in self._conversations.items():
            if user_id and conv.get("user_id") != user_id:
                continue
            if project_id and conv.get("project_id") != project_id:
                continue
            items.append({
                "conversation_id": cid,
                "title": conv.get("title"),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
                "last_message": (conv.get("messages") or [])[-1] if conv.get("messages") else None,
            })
        items.sort(key=lambda x: x.get("updated_at") or 0, reverse=True)
        return items[:limit]

    def rename_conversation(self, conversation_id: str, new_title: str, user_id: Optional[str] = None,
                            project_id: Optional[str] = None) -> None:
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

    def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None,
                            project_id: Optional[str] = None) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        if user_id and conv.get("user_id") != user_id:
            raise ChatRepositoryError("Access denied: user_id mismatch")
        if project_id and conv.get("project_id") != project_id:
            raise ChatRepositoryError("Access denied: project_id mismatch")
        del self._conversations[conversation_id]
        self._save()

    def update_summary(self, conversation_id: str, summary: Optional[str]) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ChatRepositoryError(f"Conversation not found: {conversation_id}")
        conv["summary"] = summary
        conv["updated_at"] = time()
        self._save()

    def count_conversations(self) -> int:
        return len(self._conversations)
