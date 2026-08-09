from __future__ import annotations

import inspect
from typing import Any

from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_orchestration_service import MessageOrchestrationService


class _FallbackConversationService:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def validate_conversation_access(self, *args: Any, **kwargs: Any) -> None:
        if kwargs:
            raise TypeError("unexpected keyword argument 'user_id'")
        self.calls.append(args)


def test_validate_conversation_access_fallback_misplaces_project_id_as_user_id() -> None:
    """Characterize the legacy TypeError fallback bug before refactoring it."""
    fallback = _FallbackConversationService()
    service = object.__new__(MessageOrchestrationService)
    service._conversation_service = fallback
    conversation = {"user_id": "user-1", "project_id": "project-1"}

    service._validate_conversation_access(
        "conv-1",
        conversation,
        user_id="user-1",
        project_id="project-1",
    )

    assert fallback.calls == [("conv-1", conversation, "project-1")]
    parameters = list(inspect.signature(ConversationService.validate_conversation_access).parameters)
    assert parameters == ["self", "conversation_id", "conv", "user_id", "project_id"]
    assert fallback.calls[0][2] == "project-1"  # occupies the real signature's user_id slot
