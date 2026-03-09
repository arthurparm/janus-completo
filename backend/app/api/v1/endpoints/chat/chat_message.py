import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.llm import ModelPriority
from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
    get_chat_service,
)
from app.services.intent_routing_service import get_intent_routing_service
from app.services.memory_service import MemoryService, get_memory_service
from app.services.chat.chat_citation_service import (
    MANDATORY_CITATION_GUARD_TEXT,
    build_citation_status,
    collect_chat_citations,
)
from app.services.chat_study_service import ChatStudyJobService, ChatStudyService
from app.services.chat.chat_contracts import (
    build_agent_state,
    build_confirmation_payload,
    chat_http_error_detail,
    extract_pending_action_id_from_text,
    maybe_create_fallback_pending_action,
    normalize_understanding_payload,
)

from .deps import (
    is_chat_auth_enforced,
    resolve_authenticated_user_context,
)
from .models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
)
from .policies import confidence_band, confidence_confirmation_threshold

router = APIRouter()
logger = structlog.get_logger(__name__)


def _get_chat_study_job_service(http: Request, service: ChatService) -> ChatStudyJobService:
    existing = getattr(http.app.state, "chat_study_job_service", None)
    if existing is not None:
        return existing
    study_service = ChatStudyService(
        llm_service=getattr(http.app.state, "llm_service", None),
        knowledge_service=getattr(http.app.state, "knowledge_service", None),
        autonomy_admin_service=getattr(http.app.state, "autonomy_admin_service", None),
    )
    jobs = ChatStudyJobService(study_service=study_service, chat_service=service)
    http.app.state.chat_study_job_service = jobs
    return jobs


@router.post("/start", response_model=ChatStartResponse, summary="Inicia uma nova conversa")
async def start_chat(
    request: ChatStartRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    identity_ctx = resolve_authenticated_user_context(
        http,
        request.user_id,
        allow_anonymous_fallback=True,
        endpoint_label="/api/v1/chat/start",
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
    conversation_id = await service.start_conversation_async(
        request.persona, user_id, request.project_id
    )
    return ChatStartResponse(conversation_id=conversation_id)


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Envia uma mensagem e recebe a resposta do LLM",
)
async def send_message(
    payload: ChatMessageRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
    memory: MemoryService = Depends(get_memory_service),
):
    routing_service = get_intent_routing_service()
    try:
        role, routing_decision, route_applied = routing_service.resolve_role(
            payload.role, payload.message
        )
        priority = ModelPriority(payload.priority)
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

    identity_ctx = resolve_authenticated_user_context(
        http,
        payload.user_id,
        allow_anonymous_fallback=True,
        endpoint_label="/api/v1/chat/message",
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
    if routing_decision:
        logger.info(
            "chat.intent_routing",
            conversation_id=payload.conversation_id,
            requested_role=payload.role,
            selected_role=role.value,
            intent=routing_decision.intent,
            risk_level=routing_decision.risk_level,
            confidence=routing_decision.confidence,
            route_applied=route_applied,
        )
    try:
        result: dict[str, Any] = await service.send_message(
            conversation_id=payload.conversation_id,
            message=payload.message,
            role=role,
            priority=priority,
            timeout_seconds=payload.timeout_seconds,
            user_id=user_id,
            project_id=payload.project_id,
            identity_source=identity_ctx.identity_source,
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
    except MessageTooLargeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=chat_http_error_detail(
                code="CHAT_MESSAGE_TOO_LARGE",
                message=str(e),
                category="validation",
                retryable=False,
                http_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            ),
        )
    except ChatServiceError as e:
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
        logger.error("chat_message_service_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=chat_http_error_detail(
                code="CHAT_INVOCATION_ERROR",
                message="Internal server error",
                category="internal",
                retryable=True,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )

    try:
        citation_result = await collect_chat_citations(
            message=payload.message,
            user_id=str(user_id) if user_id is not None else None,
            conversation_id=str(result.get("conversation_id") or payload.conversation_id),
            memory_service=memory,
            limit=5,
        )
        citations = citation_result.get("citations") or []
        citations_retrieval_failed = bool(citation_result.get("retrieval_failed"))
    except Exception as e:
        logger.warning("chat_message_citations_failed", error=str(e))
        citations = []
        citations_retrieval_failed = True
    result["citations"] = citations
    result["citation_status"] = build_citation_status(
        message=payload.message,
        citations=citations,
        retrieval_failed=citations_retrieval_failed,
    )
    pending_action_id = None
    try:
        if result.get("pending_action_id") is not None:
            pending_action_id = int(result.get("pending_action_id"))
    except Exception:
        pending_action_id = None
    if pending_action_id is None:
        pending_action_id = extract_pending_action_id_from_text(str(result.get("response") or ""))

    understanding = result.get("understanding")
    if isinstance(understanding, dict):
        raw_confidence = understanding.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(raw_confidence)))
        except Exception:
            confidence = 0.0
        threshold = confidence_confirmation_threshold()
        low_confidence = confidence < threshold
        intent = str(understanding.get("intent") or "")
        requires_confirmation = bool(understanding.get("requires_confirmation"))
        understanding["confidence"] = round(confidence, 2)
        understanding["confidence_band"] = confidence_band(confidence)
        understanding["low_confidence"] = low_confidence
        if low_confidence and (requires_confirmation or intent in {"action_request", "reminder"}):
            understanding["requires_confirmation"] = True
            understanding["confirmation_reason"] = "low_confidence"
            result["response"] = (
                f"Estou com baixa confianca ({int(round(confidence * 100))}%). "
                "Antes de executar essa acao, confirme se devo prosseguir."
            )

    last_assistant_message: dict[str, Any] | None = None
    if result.get("citation_status", {}).get("status") == "missing_required":
        placeholder_text = (
            "Estou estudando a base para responder com segurança. "
            "Isso pode demorar um pouco porque preciso localizar evidências rastreáveis."
        )
        result["response"] = placeholder_text
        result["delivery_status"] = "pending_study"
        result["study_notice"] = placeholder_text
        result["failure_classification"] = (
            "infra_transient"
            if result.get("citation_status", {}).get("reason") == "retrieval_error"
            else None
        )
        if hasattr(service, "get_last_assistant_message"):
            try:
                last_assistant_message = await service.get_last_assistant_message(
                    conversation_id=payload.conversation_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(
                    "chat_message_get_last_assistant_failed",
                    conversation_id=payload.conversation_id,
                    error=str(e),
                )
        if last_assistant_message and hasattr(service, "update_message_payload"):
            try:
                await service.update_message_payload(
                    conversation_id=payload.conversation_id,
                    message_id=int(last_assistant_message.get("id")),
                    patch={
                        "text": placeholder_text,
                        "citations": [],
                        "citation_status": result.get("citation_status"),
                        "delivery_status": "pending_study",
                        "failure_classification": result.get("failure_classification"),
                        "provider": result.get("provider"),
                        "model": result.get("model"),
                    },
                    user_id=user_id,
                )
                result["message_id"] = str(last_assistant_message.get("id"))
                jobs = _get_chat_study_job_service(http, service)
                job = jobs.create_job(
                    conversation_id=payload.conversation_id,
                    message_id=str(last_assistant_message.get("id")),
                    question=payload.message,
                    user_id=user_id,
                    placeholder_message=placeholder_text,
                )
                result["study_job"] = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "poll_url": f"/api/v1/chat/study-jobs/{job.job_id}",
                    "conversation_id": payload.conversation_id,
                    "message_id": str(last_assistant_message.get("id")),
                    "placeholder_message": placeholder_text,
                }
                asyncio.create_task(jobs.run_job(job_id=job.job_id, role=role, priority=priority))
            except Exception as e:
                logger.warning(
                    "chat_message_start_study_failed",
                    conversation_id=payload.conversation_id,
                    error=str(e),
                )
                result["response"] = MANDATORY_CITATION_GUARD_TEXT

    if routing_decision:
        understanding = result.get("understanding")
        if not isinstance(understanding, dict):
            understanding = {}
            result["understanding"] = understanding
        understanding["routing"] = {
            "requested_role": payload.role,
            "selected_role": role.value,
            "route_applied": route_applied,
            **routing_decision.to_dict(),
        }

        if routing_decision.risk_level == "high":
            understanding["requires_confirmation"] = True
            understanding["confirmation_reason"] = "high_risk"
            if "alto risco" not in str(result.get("response", "")).lower():
                result["response"] = (
                    "Pedido classificado como alto risco. Confirme o objetivo e o escopo antes de seguir.\n\n"
                    f"{result.get('response', '')}"
                )

    pending_action_id, fallback_reason = maybe_create_fallback_pending_action(
        user_id=str(user_id) if user_id is not None else None,
        message=payload.message,
        assistant_response=str(result.get("response") or ""),
        conversation_id=str(result.get("conversation_id") or payload.conversation_id),
        existing_pending_action_id=pending_action_id,
        understanding=understanding if isinstance(understanding, dict) else None,
    )
    if fallback_reason and isinstance(understanding, dict) and not understanding.get("confirmation_reason"):
        understanding["confirmation_reason"] = fallback_reason

    confirmation_payload = build_confirmation_payload(
        pending_action_id=pending_action_id,
        reason=(
            (understanding or {}).get("confirmation_reason")
            if isinstance(understanding, dict)
            else None
        ),
    )
    normalized_understanding = normalize_understanding_payload(
        understanding if isinstance(understanding, dict) else None,
        confirmation=confirmation_payload,
    )
    if normalized_understanding:
        result["understanding"] = normalized_understanding
    if confirmation_payload:
        result["confirmation"] = confirmation_payload
    agent_state = build_agent_state(
        understanding=normalized_understanding if isinstance(normalized_understanding, dict) else None,
        confirmation=confirmation_payload,
    )
    if agent_state:
        result["agent_state"] = agent_state

    if last_assistant_message is None and hasattr(service, "get_last_assistant_message"):
        try:
            last_assistant_message = await service.get_last_assistant_message(
                conversation_id=payload.conversation_id,
                user_id=user_id,
            )
        except Exception:
            last_assistant_message = None
    if last_assistant_message and hasattr(service, "update_message_payload"):
        try:
            await service.update_message_payload(
                conversation_id=payload.conversation_id,
                message_id=int(last_assistant_message.get("id")),
                patch={
                    "text": result.get("response"),
                    "citations": result.get("citations") or [],
                    "citation_status": result.get("citation_status"),
                    "ui": result.get("ui"),
                    "understanding": result.get("understanding"),
                    "confirmation": result.get("confirmation"),
                    "agent_state": result.get("agent_state"),
                    "delivery_status": result.get("delivery_status") or "completed",
                    "failure_classification": result.get("failure_classification"),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                },
                user_id=user_id,
            )
            result["message_id"] = str(last_assistant_message.get("id"))
        except Exception as e:
            logger.warning(
                "chat_message_persist_metadata_failed",
                conversation_id=payload.conversation_id,
                error=str(e),
            )

    return ChatMessageResponse(**result)
