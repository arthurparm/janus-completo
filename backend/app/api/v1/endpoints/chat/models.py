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
    knowledge_space_id: str | None = Field(None)


class ChatCitationStatus(BaseModel):
    mode: str = "optional"
    status: str = "not_applicable"
    count: int = 0
    reason: str | None = None


class ChatRoutingState(BaseModel):
    requested_role: str | None = None
    selected_role: str | None = None
    route_applied: bool | None = None
    intent: str | None = None
    risk_level: str | None = None
    confidence: float | None = None


class ChatRiskState(BaseModel):
    level: str | None = None
    source: str | None = None
    summary: str | None = None
    requires_confirmation: bool | None = None


class ChatConfirmationState(BaseModel):
    required: bool = True
    reason: str | None = None
    source: str | None = None
    pending_action_id: int | None = None
    approve_endpoint: str | None = None
    reject_endpoint: str | None = None


class ChatAgentState(BaseModel):
    state: str
    confidence_band: str | None = None
    requires_confirmation: bool | None = None
    reason: str | None = None


class ChatUnderstandingPayload(BaseModel):
    intent: str
    summary: str
    confidence: float | None = None
    confidence_band: str | None = None
    low_confidence: bool | None = None
    requires_confirmation: bool | None = None
    confirmation_reason: str | None = None
    signals: list[str] | None = None
    routing: ChatRoutingState | dict[str, Any] | None = None
    risk: ChatRiskState | dict[str, Any] | None = None
    confirmation: ChatConfirmationState | dict[str, Any] | None = None


class ChatMessageResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str
    conversation_id: str
    message_id: str | None = None
    knowledge_space_id: str | None = None
    mode_used: str | None = None
    base_used: str | None = None
    answer_strategy: str | None = None
    estimated_wait_seconds: int = 0
    estimated_wait_range_seconds: list[int] = Field(default_factory=list)
    processing_profile: str | None = None
    processing_notice: str | None = None
    evidence_count: int = 0
    source_roles_used: list[str] = Field(default_factory=list)
    source_scope: dict[str, Any] | None = None
    gaps_or_conflicts: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    citation_status: ChatCitationStatus = Field(default_factory=ChatCitationStatus)
    ui: dict[str, Any] | None = None
    understanding: ChatUnderstandingPayload | dict[str, Any] | None = None
    confirmation: ChatConfirmationState | dict[str, Any] | None = None
    agent_state: ChatAgentState | dict[str, Any] | None = None
    delivery_status: str | None = None
    study_job: dict[str, Any] | None = None
    study_notice: str | None = None
    failure_classification: str | None = None


class ChatMessage(BaseModel):
    message_id: str | None = None
    timestamp: float
    role: str
    text: str
    knowledge_space_id: str | None = None
    mode_used: str | None = None
    base_used: str | None = None
    answer_strategy: str | None = None
    estimated_wait_seconds: int = 0
    estimated_wait_range_seconds: list[int] = Field(default_factory=list)
    processing_profile: str | None = None
    processing_notice: str | None = None
    evidence_count: int = 0
    source_roles_used: list[str] = Field(default_factory=list)
    source_scope: dict[str, Any] | None = None
    gaps_or_conflicts: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    citation_status: ChatCitationStatus | dict[str, Any] | None = None
    ui: dict[str, Any] | None = None
    understanding: ChatUnderstandingPayload | dict[str, Any] | None = None
    confirmation: ChatConfirmationState | dict[str, Any] | None = None
    agent_state: ChatAgentState | dict[str, Any] | None = None
    delivery_status: str | None = None
    failure_classification: str | None = None
    provider: str | None = None
    model: str | None = None


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
