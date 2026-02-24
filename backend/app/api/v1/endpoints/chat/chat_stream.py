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

from .deps import acquire_sse_slot, actor_project_id, actor_user_id, ensure_origin_allowed, release_sse_slot

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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid role or priority"
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
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Message too large"
            )

    slot_user: str | None = None
    try:
        if not user_id:
            user_id = actor_user_id(http)
        if not project_id:
            project_id = actor_project_id(http)

        slot_user = await acquire_sse_slot(str(user_id) if user_id is not None else None)
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
):
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
        if not user_id:
            user_id = actor_user_id(http)
        slot_user = await acquire_sse_slot(str(user_id) if user_id is not None else None)
        gen = service.stream_events(conversation_id=conversation_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting event stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
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
