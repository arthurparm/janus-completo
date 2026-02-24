"""
Custom exceptions for Chat Service.
Provides specific exception types for better error handling and debugging.
"""


class ChatServiceError(Exception):
    """Base exception for chat service errors."""

    pass


class ConversationNotFoundError(ChatServiceError):
    """Raised when a conversation doesn't exist."""

    def __init__(self, conv_id: str):
        self.conv_id = conv_id
        super().__init__(f"Conversation '{conv_id}' not found")


class PromptBuildError(ChatServiceError):
    """Failed to build prompt for LLM."""

    def __init__(self, reason: str, context: dict | None = None):
        self.reason = reason
        self.context = context or {}
        super().__init__(f"Prompt build failed: {reason}")


class ToolExecutionError(ChatServiceError):
    """Tool execution failed during agent loop."""

    def __init__(self, tool_name: str, error: Exception):
        self.tool_name = tool_name
        self.original_error = error
        super().__init__(f"Tool '{tool_name}' failed: {error}")


class MemoryRetrievalError(ChatServiceError):
    """Memory/RAG context retrieval failed."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Memory retrieval failed: {reason}")


class ConversationAccessDeniedError(ChatServiceError):
    """User doesn't have access to conversation."""

    def __init__(self, conv_id: str, user_id: str):
        self.conv_id = conv_id
        self.user_id = user_id
        super().__init__(f"User '{user_id}' cannot access conversation '{conv_id}'")


class RateLimitError(ChatServiceError):
    """Rate limit exceeded for user/project."""

    def __init__(self, resource: str, limit: int):
        self.resource = resource
        self.limit = limit
        super().__init__(f"Rate limit exceeded for '{resource}': {limit}/hour")


class MessageTooLargeError(ChatServiceError):
    """Message payload exceeds configured size."""

    def __init__(self, size_bytes: int, limit_bytes: int):
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"Message too large ({size_bytes} bytes > {limit_bytes} bytes)"
        )


class LLMInvocationError(ChatServiceError):
    """LLM invocation failed."""

    def __init__(self, provider: str, model: str, error: Exception):
        self.provider = provider
        self.model = model
        self.original_error = error
        super().__init__(f"LLM invocation failed ({provider}/{model}): {error}")
