from __future__ import annotations

import asyncio
from typing import Any


class AsyncChatRepositoryPort:
    """Async boundary for the synchronous chat repository.

    ChatRepositorySQL opens and closes a session per operation when it is not
    given an explicit session, so moving one complete operation to a worker
    thread does not share a live SQLAlchemy session across threads.
    """

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._repository.get_conversation, conversation_id)

    async def get_recent_messages(
        self,
        conversation_id: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._repository.get_recent_messages,
            conversation_id,
            limit=limit,
        )

    async def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._repository.add_message,
            conversation_id,
            role=role,
            text=text,
            metadata=metadata,
        )
