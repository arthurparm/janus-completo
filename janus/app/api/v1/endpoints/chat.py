import structlog
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chat_service import ChatService, get_chat_service, ChatServiceError, ConversationNotFoundError
from app.core.llm import ModelRole, ModelPriority

router = APIRouter(tags=["Chat"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class ChatStartRequest(BaseModel):
    persona: Optional[str] = Field(None)
    user_id: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)
    title: Optional[str] = Field(None)


class ChatStartResponse(BaseModel):
    conversation_id: str


class ChatMessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=3)
    message: str = Field(..., min_length=1)
    role: str = Field("orchestrator")
    priority: str = Field("fast_and_cheap")
    timeout_seconds: Optional[int] = None
    user_id: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)


class ChatMessageResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str
    conversation_id: str


class ChatMessage(BaseModel):
    timestamp: float
    role: str
    text: str


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    persona: Optional[str]
    messages: List[ChatMessage]


class ChatRenameRequest(BaseModel):
    new_title: str = Field(..., min_length=1)
    user_id: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)


class ChatListResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    created_at: Optional[float]
    updated_at: Optional[float]
    last_message: Optional[ChatMessage]


# --- Endpoints ---

@router.post("/start", response_model=ChatStartResponse, summary="Inicia uma nova conversa")
async def start_chat(request: ChatStartRequest, service: ChatService = Depends(get_chat_service), http: Request = None):
    hdr_uid = None
    try:
        hdr_uid = (getattr(http.state, "actor_user_id", None) if http else None)
    except Exception:
        hdr_uid = None
    user_id = request.user_id or hdr_uid or None
    conversation_id = service.start_conversation(request.persona, user_id, request.project_id)
    return ChatStartResponse(conversation_id=conversation_id)


@router.post("/message", response_model=ChatMessageResponse, summary="Envia uma mensagem e recebe a resposta do LLM")
async def send_message(payload: ChatMessageRequest, service: ChatService = Depends(get_chat_service), http: Request = None):
    try:
        role = ModelRole(payload.role)
        priority = ModelPriority(payload.priority)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role or priority")

    hdr_uid = None
    try:
        hdr_uid = (getattr(http.state, "actor_user_id", None) if http else None)
    except Exception:
        hdr_uid = None
    try:
        result: Dict[str, Any] = service.send_message(
            conversation_id=payload.conversation_id,
            message=payload.message,
            role=role,
            priority=priority,
            timeout_seconds=payload.timeout_seconds,
            user_id=payload.user_id or hdr_uid,
            project_id=payload.project_id,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return ChatMessageResponse(**result)


@router.get("/{conversation_id}/history", response_model=ChatHistoryResponse, summary="Retorna o histórico da conversa")
async def chat_history(conversation_id: str, service: ChatService = Depends(get_chat_service)):
    try:
        hist = service.get_history(conversation_id)
        # Convert dict messages to DTOs
        messages = [ChatMessage(**m) for m in hist.get("messages", [])]
        return ChatHistoryResponse(conversation_id=hist["conversation_id"], persona=hist.get("persona"),
                                   messages=messages)
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/conversations", response_model=List[ChatListResponse], summary="Lista conversas com filtros de RBAC")
async def list_conversations(user_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50,
                             service: ChatService = Depends(get_chat_service), http: Request = None):
    try:
        hdr_uid = (getattr(http.state, "actor_user_id", None) if http else None)
    except Exception:
        hdr_uid = None
    items = service.list_conversations(user_id=user_id or hdr_uid, project_id=project_id, limit=limit)

    # map items to DTOs
    def map_item(it: Dict[str, Any]) -> ChatListResponse:
        last = it.get("last_message")
        last_msg = ChatMessage(**last) if isinstance(last, dict) else None
        return ChatListResponse(
            conversation_id=it.get("conversation_id"),
            title=it.get("title"),
            created_at=it.get("created_at"),
            updated_at=it.get("updated_at"),
            last_message=last_msg,
        )

    return [map_item(it) for it in items]


@router.put("/{conversation_id}/rename", summary="Renomeia uma conversa")
async def rename_conversation(conversation_id: str, payload: ChatRenameRequest,
                              service: ChatService = Depends(get_chat_service), http: Request = None):
    try:
        hdr_uid = None
        try:
            hdr_uid = (getattr(http.state, "actor_user_id", None) if http else None)
        except Exception:
            hdr_uid = None
        service.rename_conversation(conversation_id, payload.new_title, user_id=payload.user_id or hdr_uid,
                                    project_id=payload.project_id)
        return {"status": "ok"}
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.delete("/{conversation_id}", summary="Apaga uma conversa")
async def delete_conversation(conversation_id: str, user_id: Optional[str] = None, project_id: Optional[str] = None,
                              service: ChatService = Depends(get_chat_service), http: Request = None):
    try:
        hdr_uid = None
        try:
            hdr_uid = (getattr(http.state, "actor_user_id", None) if http else None)
        except Exception:
            hdr_uid = None
        service.delete_conversation(conversation_id, user_id=user_id or hdr_uid, project_id=project_id)
        return {"status": "ok"}
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/stream/{conversation_id}", summary="Streaming de resposta via SSE")
async def stream_message(conversation_id: str, message: str, role: str = "orchestrator",
                         priority: str = "fast_and_cheap", timeout_seconds: Optional[int] = None,
                         user_id: Optional[str] = None, project_id: Optional[str] = None,
                         service: ChatService = Depends(get_chat_service)):
    # valida enum
    try:
        role_enum = ModelRole(role)
        priority_enum = ModelPriority(priority)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role or priority")

    try:
        gen = service.stream_message(
            conversation_id=conversation_id,
            message=message,
            role=role_enum,
            priority=priority_enum,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return StreamingResponse(gen, media_type="text/event-stream")
