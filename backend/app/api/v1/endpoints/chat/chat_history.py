from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    get_chat_service,
)

from .deps import (
    actor_project_id,
    is_chat_auth_enforced,
    resolve_authenticated_user_context,
)
from .models import (
    ChatHistoryPaginatedResponse,
    ChatHistoryResponse,
    ChatListResponse,
    ChatMessage,
    apply_ui_to_message,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/{conversation_id}/history",
    response_model=ChatHistoryResponse,
    summary="Retorna o histórico da conversa",
)
async def chat_history(
    conversation_id: str,
    limit: int | None = None,
    offset: int = 0,
    before_ts: float | None = None,
    after_ts: float | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    logger.info(
        "chat_history_request",
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )

    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            None,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/history",
        )
        user_id = identity_ctx.user_id
        if user_id is None and is_chat_auth_enforced():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
            )
        project_id = actor_project_id(http)

        if limit is not None:
            hist = service.get_history_paginated(
                conversation_id=conversation_id,
                limit=limit,
                offset=offset,
                before_ts=before_ts,
                after_ts=after_ts,
                user_id=user_id,
                project_id=project_id,
            )

            messages = []
            for i, message in enumerate(hist.get("messages", [])):
                try:
                    if (
                        isinstance(message, dict)
                        and "timestamp" in message
                        and "role" in message
                        and "text" in message
                    ):
                        messages.append(ChatMessage(**apply_ui_to_message(message)))
                    else:
                        logger.warning("chat_history_invalid_message_skipped", index=i)
                except Exception as e:
                    logger.warning("chat_history_message_conversion_failed", index=i, error=str(e))

            return ChatHistoryResponse(
                conversation_id=hist["conversation_id"],
                persona=hist.get("persona"),
                messages=messages,
            )

        hist = service.get_history(
            conversation_id,
            user_id=user_id,
            project_id=project_id,
        )
        messages = []
        for i, message in enumerate(hist.get("messages", [])):
            try:
                if (
                    isinstance(message, dict)
                    and "timestamp" in message
                    and "role" in message
                    and "text" in message
                ):
                    messages.append(ChatMessage(**apply_ui_to_message(message)))
                else:
                    logger.warning("chat_history_invalid_message_skipped", index=i)
            except Exception as e:
                logger.warning("chat_history_message_conversion_failed", index=i, error=str(e))

        return ChatHistoryResponse(
            conversation_id=hist["conversation_id"],
            persona=hist.get("persona"),
            messages=messages,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError as e:
        if "Access denied" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Access denied", "code": "CHAT_ACCESS_DENIED"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/{conversation_id}/history/paginated",
    response_model=ChatHistoryPaginatedResponse,
    summary="Retorna o histórico da conversa com paginação e RBAC",
)
async def chat_history_paginated(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    before_ts: float | None = None,
    after_ts: float | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    identity_ctx = resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/history/paginated",
    )
    user_id = identity_ctx.user_id
    if user_id is None and is_chat_auth_enforced():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
        )
    project_id = actor_project_id(http)
    try:
        hist = service.get_history_paginated(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            before_ts=before_ts,
            after_ts=after_ts,
            user_id=user_id,
            project_id=project_id,
        )

        messages = []
        for i, message in enumerate(hist.get("messages", [])):
            try:
                if (
                    isinstance(message, dict)
                    and "timestamp" in message
                    and "role" in message
                    and "text" in message
                ):
                    messages.append(ChatMessage(**apply_ui_to_message(message)))
                else:
                    logger.warning("chat_history_invalid_message_skipped", index=i)
            except Exception as e:
                logger.warning("chat_history_message_conversion_failed", index=i, error=str(e))

        return ChatHistoryPaginatedResponse(
            conversation_id=hist["conversation_id"],
            persona=hist.get("persona"),
            messages=messages,
            total_count=hist.get("total_count", 0),
            has_more=hist.get("has_more", False),
            next_offset=hist.get("next_offset"),
            limit=hist.get("limit", limit),
            offset=hist.get("offset", offset),
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError as e:
        if "Access denied" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Access denied", "code": "CHAT_ACCESS_DENIED"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/conversations",
    response_model=list[ChatListResponse],
    summary="Lista conversas com filtros de RBAC",
)
async def list_conversations(
    project_id: str | None = None,
    limit: int = 50,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    identity_ctx = resolve_authenticated_user_context(
        http,
        user_id,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/conversations",
    )
    final_user_id = identity_ctx.user_id
    if final_user_id is None and is_chat_auth_enforced():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
        )
    items = await service.list_conversations(
        user_id=final_user_id,
        project_id=project_id,
        limit=limit,
    )

    def map_item(item: dict[str, Any]) -> ChatListResponse:
        last = item.get("last_message")
        last_msg = ChatMessage(**apply_ui_to_message(last)) if isinstance(last, dict) else None
        return ChatListResponse(
            conversation_id=item.get("conversation_id"),
            title=item.get("title"),
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
            last_message=last_msg,
        )

    return [map_item(item) for item in items]
