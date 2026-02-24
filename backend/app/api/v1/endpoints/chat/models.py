from typing import Any

from pydantic import BaseModel, Field


class ChatStartRequest(BaseModel):
    persona: str | None = Field(None)
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)
    title: str | None = Field(None)


class ChatStartResponse(BaseModel):
    conversation_id: str


class ChatMessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    role: str = Field("auto")
    priority: str = Field("fast_and_cheap")
    timeout_seconds: int | None = None
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)


class ChatMessageResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str
    conversation_id: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    ui: dict[str, Any] | None = None
    understanding: dict[str, Any] | None = None


class ChatMessage(BaseModel):
    timestamp: float
    role: str
    text: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    ui: dict[str, Any] | None = None
    understanding: dict[str, Any] | None = None


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    persona: str | None
    messages: list[ChatMessage]


class ChatHistoryPaginatedResponse(BaseModel):
    conversation_id: str
    persona: str | None
    messages: list[ChatMessage]
    total_count: int
    has_more: bool
    next_offset: int | None
    limit: int
    offset: int


class ChatRenameRequest(BaseModel):
    new_title: str = Field(..., min_length=1)
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)


class ChatListResponse(BaseModel):
    conversation_id: str
    title: str | None
    created_at: float | None
    updated_at: float | None
    last_message: ChatMessage | None
    message_count: int | None = None
    tags: list[str] = Field(default_factory=list)
    last_message_at: str | None = None


def apply_ui_to_message(message: dict[str, Any]) -> dict[str, Any]:
    return dict(message)
