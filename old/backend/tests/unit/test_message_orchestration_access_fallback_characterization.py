from __future__ import annotations

from typing import Any

from app.services.chat.message_orchestration_service import MessageOrchestrationService


class _ConversationServiceSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def validate_conversation_access(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((*args, kwargs))


def test_validate_conversation_access_uses_explicit_owner_and_project_scope() -> None:
    """Regression test for the unsafe fallback captured by the golden baseline."""
    conversation_service = _ConversationServiceSpy()
    service = object.__new__(MessageOrchestrationService)
    service._conversation_service = conversation_service
    conversation = {"user_id": "user-1", "project_id": "project-1"}

    service._validate_conversation_access(
        "conv-1",
        conversation,
        user_id="user-1",
        project_id="project-1",
    )

    assert conversation_service.calls == [
        (
            "conv-1",
            conversation,
            {"user_id": "user-1", "project_id": "project-1"},
        )
    ]
