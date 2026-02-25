import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.llm import ModelPriority
from app.services.chat_service import (
    ChatService,
    ConversationNotFoundError,
    get_chat_service,
)
from app.services.intent_routing_service import get_intent_routing_service
from app.services.trace_service import TraceService, get_trace_service
from app.services.chat.chat_contracts import chat_http_error_detail

from .deps import (
    acquire_sse_slot,
    actor_project_id,
    ensure_origin_allowed,
    is_chat_auth_enforced,
    release_sse_slot,
    resolve_authenticated_user_context,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/stream/{conversation_id}", summary="Streaming de resposta via SSE")
async def stream_message(
    conversation_id: str,
    message: str,
    role: str = "auto",
    priority: str = "fast_and_cheap",
    timeout_seconds: int | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    routing_service = get_intent_routing_service()
    try:
        role_enum, routing_decision, route_applied = routing_service.resolve_role(role, message)
        priority_enum = ModelPriority(priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=chat_http_error_detail(
                code="CHAT_INVALID_ROLE_OR_PRIORITY",
                message="Invalid role or priority",
                category="validation",
                retryable=False,
                http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
        )

    if routing_decision:
        logger.info(
            "chat.intent_routing.stream",
            conversation_id=conversation_id,
            requested_role=role,
            selected_role=role_enum.value,
            intent=routing_decision.intent,
            risk_level=routing_decision.risk_level,
            confidence=routing_decision.confidence,
            route_applied=route_applied,
        )

    ensure_origin_allowed(http)

    if message:
        try:
            message_size = len(message.encode("utf-8"))
        except Exception:
            message_size = len(message)
        if message_size > 10 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=chat_http_error_detail(
                    code="CHAT_MESSAGE_TOO_LARGE",
                    message="Message too large",
                    category="validation",
                    retryable=False,
                    http_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                ),
            )

    slot_user: str | None = None
    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            user_id,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/stream",
        )
        user_id = identity_ctx.user_id
        if user_id is None and is_chat_auth_enforced():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=chat_http_error_detail(
                    code="CHAT_AUTH_REQUIRED",
                    message="Authentication required",
                    category="auth",
                    retryable=False,
                    http_status=status.HTTP_401_UNAUTHORIZED,
                ),
            )
        if not project_id:
            project_id = actor_project_id(http)
        try:
            service.get_history(
                conversation_id,
                user_id=user_id,
                project_id=project_id,
            )
        except ConversationNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=chat_http_error_detail(
                    code="CHAT_CONVERSATION_NOT_FOUND",
                    message="Conversation not found",
                    category="not_found",
                    retryable=False,
                    http_status=status.HTTP_404_NOT_FOUND,
                ),
            )
        except Exception as e:
            if "Access denied" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=chat_http_error_detail(
                        code="CHAT_ACCESS_DENIED",
                        message="Access denied",
                        category="authz",
                        retryable=False,
                        http_status=status.HTTP_403_FORBIDDEN,
                    ),
                )
            raise

        slot_user = await acquire_sse_slot(str(user_id) if user_id is not None else None)
        gen = service.stream_message(
            conversation_id=conversation_id,
            message=message,
            role=role_enum,
            priority=priority_enum,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            identity_source=identity_ctx.identity_source,
            requested_role=role,
            routing_decision=routing_decision,
            route_applied=route_applied,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=chat_http_error_detail(
                code="CHAT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
                category="not_found",
                retryable=False,
                http_status=status.HTTP_404_NOT_FOUND,
            ),
        )

    headers = {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def guarded_gen():
        try:
            async for chunk in gen:
                yield chunk
        finally:
            if slot_user is not None:
                await release_sse_slot(slot_user)

    return StreamingResponse(guarded_gen(), media_type="text/event-stream", headers=headers)


@router.get(
    "/{conversation_id}/trace", summary="Retorna o rastro de execução (Chain of Thought)"
)
async def get_conversation_trace(
    conversation_id: str,
    service: TraceService = Depends(get_trace_service),
    chat_service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    identity_ctx = resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/trace",
    )
    user_id = identity_ctx.user_id
    if user_id is None and is_chat_auth_enforced():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=chat_http_error_detail(
                code="CHAT_AUTH_REQUIRED",
                message="Authentication required",
                category="auth",
                retryable=False,
                http_status=status.HTTP_401_UNAUTHORIZED,
            ),
        )
    try:
        chat_service.get_history(conversation_id, user_id=user_id, project_id=actor_project_id(http))
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=chat_http_error_detail(
                code="CHAT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
                category="not_found",
                retryable=False,
                http_status=status.HTTP_404_NOT_FOUND,
            ),
        )
    except Exception as e:
        if "Access denied" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=chat_http_error_detail(
                    code="CHAT_ACCESS_DENIED",
                    message="Access denied",
                    category="authz",
                    retryable=False,
                    http_status=status.HTTP_403_FORBIDDEN,
                ),
            )
        raise
    return service.get_trace_history(conversation_id)


@router.get(
    "/{conversation_id}/events", summary="Streaming de eventos de agentes (observabilidade)"
)
async def stream_agent_events(
    conversation_id: str,
    user_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    ensure_origin_allowed(http)

    slot_user: str | None = None
    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            user_id,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/events",
        )
        user_id = identity_ctx.user_id
        if user_id is None and is_chat_auth_enforced():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=chat_http_error_detail(
                    code="CHAT_AUTH_REQUIRED",
                    message="Authentication required",
                    category="auth",
                    retryable=False,
                    http_status=status.HTTP_401_UNAUTHORIZED,
                ),
            )
        try:
            service.get_history(conversation_id, user_id=user_id)
        except ConversationNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=chat_http_error_detail(
                    code="CHAT_CONVERSATION_NOT_FOUND",
                    message="Conversation not found",
                    category="not_found",
                    retryable=False,
                    http_status=status.HTTP_404_NOT_FOUND,
                ),
            )
        except Exception as e:
            if "Access denied" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=chat_http_error_detail(
                        code="CHAT_ACCESS_DENIED",
                        message="Access denied",
                        category="authz",
                        retryable=False,
                        http_status=status.HTTP_403_FORBIDDEN,
                    ),
                )
            raise
        slot_user = await acquire_sse_slot(str(user_id) if user_id is not None else None)
        gen = service.stream_events(conversation_id=conversation_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_event_stream_start_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=chat_http_error_detail(
                code="CHAT_EVENT_STREAM_START_FAILED",
                message="Internal server error",
                category="internal",
                retryable=True,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )

    headers = {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def guarded_gen():
        try:
            async for chunk in gen:
                yield chunk
        finally:
            if slot_user is not None:
                await release_sse_slot(slot_user)

    return StreamingResponse(guarded_gen(), media_type="text/event-stream", headers=headers)
