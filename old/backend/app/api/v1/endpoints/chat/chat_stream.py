import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_stream_repository import (
    ChatStreamIdempotencyConflict,
    ChatStreamRepositoryError,
)
from app.services.chat.chat_contracts import chat_http_error_detail
from app.services.chat.input_policy import validate_chat_message_size
from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
    get_chat_service,
)
from app.services.chat_stream_run_service import (
    ChatStreamRunService,
    InvalidChatStreamIdempotencyKey,
    chat_stream_request_fingerprint,
    get_chat_stream_run_service,
    validate_chat_stream_idempotency_key,
)
from app.services.intent_routing_service import get_intent_routing_service
from app.services.trace_service import TraceService, get_trace_service

from .deps import (
    acquire_sse_slot,
    actor_project_id,
    ensure_origin_allowed,
    release_sse_slot,
    resolve_authenticated_user_context,
)
from .models import ChatStreamRequest

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/stream/{conversation_id}",
    summary="Streaming de resposta via SSE",
    openapi_extra={
        "parameters": [
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "minLength": 16, "maxLength": 128},
                "description": "Opaque key identifying one logical chat command.",
            },
            {
                "name": "Last-Event-ID",
                "in": "header",
                "required": False,
                "schema": {"type": "integer", "minimum": 0},
                "description": "Last persisted SSE sequence received by this subscriber.",
            },
        ]
    },
)
async def stream_message(
    conversation_id: str,
    service: ChatService = Depends(get_chat_service),
    run_service: ChatStreamRunService = Depends(get_chat_stream_run_service),
    http: Request = None,
):
    ensure_origin_allowed(http)

    identity_ctx = resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/stream",
    )
    user_id = identity_ctx.user_id
    if user_id is None:
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
        owner_user_id = int(str(user_id))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=chat_http_error_detail(
                code="CHAT_IDENTITY_INVALID",
                message="Authentication required",
                category="auth",
                retryable=False,
                http_status=status.HTTP_401_UNAUTHORIZED,
            ),
        )

    try:
        idempotency_key = validate_chat_stream_idempotency_key(
            http.headers.get("Idempotency-Key")
        )
    except InvalidChatStreamIdempotencyKey as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=chat_http_error_detail(
                code="CHAT_IDEMPOTENCY_KEY_INVALID",
                message=str(exc),
                category="validation",
                retryable=False,
                http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
        )

    raw_last_event_id = str(http.headers.get("Last-Event-ID") or "").strip()
    try:
        last_event_id = int(raw_last_event_id) if raw_last_event_id else 0
        if last_event_id < 0:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=chat_http_error_detail(
                code="CHAT_LAST_EVENT_ID_INVALID",
                message="Last-Event-ID must be a non-negative integer",
                category="validation",
                retryable=False,
                http_status=status.HTTP_400_BAD_REQUEST,
            ),
        )

    try:
        payload = ChatStreamRequest.model_validate(await http.json())
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "type": "json_invalid",
                    "loc": ["body"],
                    "msg": "Invalid JSON body",
                    "input": None,
                }
            ],
        )

    message = payload.message
    role = payload.role
    priority = payload.priority
    timeout_seconds = payload.timeout_seconds
    project_id = payload.project_id
    knowledge_space_id = payload.knowledge_space_id
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

    try:
        validate_chat_message_size(message)
    except MessageTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=chat_http_error_detail(
                code="CHAT_MESSAGE_TOO_LARGE",
                message="Message too large",
                category="validation",
                retryable=False,
                http_status=status.HTTP_413_CONTENT_TOO_LARGE,
            ),
        )

    slot_user: str | None = None
    try:
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
        project_id = actor_project_id(http) or project_id
        active_knowledge_space_id = await service.resolve_authorized_knowledge_space_id(
            conversation_id=conversation_id,
            user_id=user_id,
            project_id=project_id,
            requested_knowledge_space_id=knowledge_space_id,
        )
        if active_knowledge_space_id:
            knowledge_space_id = active_knowledge_space_id
            role_enum = ModelRole.ORCHESTRATOR
            route_applied = False
        slot_user = await acquire_sse_slot(
            channel="chat_stream",
            user_id=user_id,
        )
        fingerprint = chat_stream_request_fingerprint(
            conversation_id=conversation_id,
            payload=payload.model_dump(mode="json"),
        )

        def producer_factory():
            return service.stream_message(
                conversation_id=conversation_id,
                message=message,
                role=role_enum,
                priority=priority_enum,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                project_id=project_id,
                knowledge_space_id=knowledge_space_id,
                identity_source=identity_ctx.identity_source,
                requested_role=role,
                routing_decision=routing_decision,
                route_applied=route_applied,
            )

        try:
            attachment = await run_service.begin_or_attach(
                owner_user_id=owner_user_id,
                session_id=conversation_id,
                request_id=idempotency_key,
                request_fingerprint=fingerprint,
                producer_factory=producer_factory,
            )
        except ChatStreamIdempotencyConflict:
            await release_sse_slot(slot_user, channel="chat_stream")
            slot_user = None
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=chat_http_error_detail(
                    code="CHAT_IDEMPOTENCY_CONFLICT",
                    message="Idempotency key was already used with a different request",
                    category="conflict",
                    retryable=False,
                    http_status=status.HTTP_409_CONFLICT,
                ),
            )
        except ChatStreamRepositoryError as exc:
            await release_sse_slot(slot_user, channel="chat_stream")
            slot_user = None
            logger.error(
                "chat_stream_ledger_unavailable",
                error_type=type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=chat_http_error_detail(
                    code="CHAT_STREAM_LEDGER_UNAVAILABLE",
                    message="Chat stream temporarily unavailable",
                    category="availability",
                    retryable=True,
                    http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                ),
            )
        except Exception as exc:
            await release_sse_slot(slot_user, channel="chat_stream")
            slot_user = None
            logger.error(
                "chat_stream_ledger_unavailable",
                error_type=type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=chat_http_error_detail(
                    code="CHAT_STREAM_LEDGER_UNAVAILABLE",
                    message="Chat stream temporarily unavailable",
                    category="availability",
                    retryable=True,
                    http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                ),
            )
        gen = run_service.stream_events(
            run_id=attachment.run.id,
            owner_user_id=owner_user_id,
            after_sequence=last_event_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=chat_http_error_detail(
                code="CHAT_CONVERSATION_NOT_FOUND",
                message="Conversation not found",
                category="not_found",
                retryable=False,
                http_status=status.HTTP_404_NOT_FOUND,
            ),
        ) from exc
    except ChatServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=chat_http_error_detail(
                code="CHAT_ACCESS_DENIED",
                message="Access denied",
                category="authz",
                retryable=False,
                http_status=status.HTTP_403_FORBIDDEN,
            ),
        ) from exc

    headers = {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Idempotency-Key": idempotency_key,
        "X-Chat-Stream-Run-ID": attachment.run.id,
    }

    async def guarded_gen():
        try:
            async for chunk in gen:
                yield chunk
        finally:
            if slot_user is not None:
                await release_sse_slot(slot_user, channel="chat_stream")

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
    if user_id is None:
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
    return service.get_trace(conversation_id)


@router.get(
    "/{conversation_id}/events", summary="Streaming de eventos de agentes (observabilidade)"
)
async def stream_agent_events(
    conversation_id: str,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    ensure_origin_allowed(http)

    slot_user: str | None = None
    try:
        identity_ctx = resolve_authenticated_user_context(
            http,
            None,
            allow_anonymous_fallback=False,
            endpoint_label="/api/v1/chat/events",
        )
        user_id = identity_ctx.user_id
        if user_id is None:
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
        get_history = getattr(service, "get_history", None)
        if callable(get_history):
            try:
                get_history(conversation_id, user_id=user_id, project_id=actor_project_id(http))
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
        slot_user = await acquire_sse_slot(
            channel="agent_events",
            user_id=user_id,
        )
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
                await release_sse_slot(slot_user, channel="agent_events")

    return StreamingResponse(guarded_gen(), media_type="text/event-stream", headers=headers)
