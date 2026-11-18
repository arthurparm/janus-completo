from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation_service import ConversationService
    from .message_orchestration_service import MessageOrchestrationService
    from .streaming_service import StreamingService

__all__ = [
    "ConversationService",
    "MessageOrchestrationService",
    "StreamingService",
]


def __getattr__(name: str):
    if name == "ConversationService":
        from .conversation_service import ConversationService

        return ConversationService
    if name == "MessageOrchestrationService":
        from .message_orchestration_service import MessageOrchestrationService

        return MessageOrchestrationService
    if name == "StreamingService":
        from .streaming_service import StreamingService

        return StreamingService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
