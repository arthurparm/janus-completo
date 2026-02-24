import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    get_chat_service,
)

from .deps import actor_user_id
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
        await service.rename_conversation(
            conversation_id,
            payload.new_title,
            user_id=payload.user_id or actor_user_id(http),
            project_id=payload.project_id,
        )
        return {"status": "ok"}
    except ChatServiceError:
        logger.warning("Access denied renaming conversation", conversation_id=conversation_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


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
        logger.error("log_error", message=f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chat service unhealthy"
        )


@router.delete("/{conversation_id}", summary="Apaga uma conversa")
async def delete_conversation(
    conversation_id: str,
    user_id: str | None = None,
    project_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        await service.delete_conversation(
            conversation_id,
            user_id=user_id or actor_user_id(http),
            project_id=project_id,
        )
        return {"status": "ok"}
    except ChatServiceError:
        logger.warning("Access denied deleting conversation", conversation_id=conversation_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
