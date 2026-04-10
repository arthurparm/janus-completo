import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    get_chat_service,
)

from .deps import (
    is_chat_auth_enforced,
    resolve_authenticated_user_context,
)
from .models import ChatRenameRequest

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.put("/{conversation_id}/rename", summary="Renomeia uma conversa")
async def rename_conversation(
    conversation_id: str,
    payload: ChatRenameRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            payload.user_id,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/rename",
        )
        user_id = identity_ctx.user_id
        if user_id is None and is_chat_auth_enforced():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
            )
        await service.rename_conversation(
            conversation_id,
            payload.new_title,
            user_id=user_id,
            project_id=payload.project_id,
        )
        return {"status": "ok"}
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError:
        logger.warning("Access denied renaming conversation", conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Access denied", "code": "CHAT_ACCESS_DENIED"},
        )


@router.get("/health", summary="Verifica o status do serviço de chat")
async def chat_health(service: ChatService = Depends(get_chat_service)):
    try:
        total_conversations = await asyncio.to_thread(service._repo.count_conversations)
        await service.list_conversations(limit=1)
        return {
            "status": "healthy",
            "repository_accessible": True,
            "non_destructive_probe": True,
            "total_conversations": total_conversations,
        }
    except Exception as e:
        logger.error("chat_health_check_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chat service unhealthy"
        )


@router.delete("/{conversation_id}", summary="Apaga uma conversa")
async def delete_conversation(
    conversation_id: str,
    project_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            user_id,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/delete",
        )
        resolved_user_id = identity_ctx.user_id
        if resolved_user_id is None and is_chat_auth_enforced():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
            )
        await service.delete_conversation(
            conversation_id,
            user_id=resolved_user_id,
            project_id=project_id,
        )
        return {"status": "ok"}
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError:
        logger.warning("Access denied deleting conversation", conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Access denied", "code": "CHAT_ACCESS_DENIED"},
        )
