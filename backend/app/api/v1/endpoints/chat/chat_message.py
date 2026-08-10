import asyncio
from typing import Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app.core.llm import ModelPriority, ModelRole
from app.services.chat.chat_citation_service import (
    build_citation_status,
    build_missing_citation_resolution,
    citation_collection_timeout_seconds,
    collect_chat_citations,
    collect_chat_citations_with_deadline,
    references_uploaded_material,
    requires_mandatory_citations,
)
from app.services.chat.chat_contracts import (
    chat_http_error_detail,
    extract_pending_action_id_from_text,
    maybe_create_fallback_pending_action,
)
from app.services.chat.turn_core import (
    ChatTurnFinalizer,
    TurnBusinessState,
    TurnExecutionResult,
    build_routed_understanding,
    infer_turn_strategy,
)
from app.services.chat_rest_run_service import (
    ChatRestAttachment,
    ChatRestIdempotencyConflict,
    ChatRestRequestInProgress,
    ChatRestRunService,
    chat_rest_request_fingerprint,
    get_chat_rest_run_service,
    validate_chat_rest_idempotency_key,
)
from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
    get_chat_service,
)
from app.services.chat_study_service import ChatStudyJobService, ChatStudyService
from app.services.intent_routing_service import get_intent_routing_service
from app.services.memory_service import MemoryService, get_memory_service

from .deps import actor_project_id, resolve_authenticated_user_context
from .models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
)
from .policies import confidence_band, confidence_confirmation_threshold

router = APIRouter()
logger = structlog.get_logger(__name__)
CITATION_COLLECTION_TIMEOUT_SECONDS = citation_collection_timeout_seconds()


def _required_int(value: Any, *, field_name: str) -> int:
    if value is None:
        raise ValueError(f"{field_name} is required")
    return int(value)


def _bounded_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _get_chat_study_job_service(http: Request, service: ChatService) -> ChatStudyJobService:
    existing = getattr(http.app.state, "chat_study_job_service", None)
    if existing is not None:
        return cast(ChatStudyJobService, existing)
    if hasattr(service, "get_study_job_service"):
        jobs = service.get_study_job_service()
        http.app.state.chat_study_job_service = jobs
        return cast(ChatStudyJobService, jobs)
    study_service = ChatStudyService(
        llm_service=getattr(http.app.state, "llm_service", None),
        knowledge_service=getattr(http.app.state, "knowledge_service", None),
        autonomy_admin_service=getattr(http.app.state, "autonomy_admin_service", None),
    )
    jobs = ChatStudyJobService(study_service=study_service, chat_service=service)
    http.app.state.chat_study_job_service = jobs
    return jobs


async def _collect_chat_citations_with_deadline(
    *,
    message: str,
    conversation_id: str,
    memory: MemoryService,
    limit: int,
) -> dict[str, Any]:
    return await collect_chat_citations_with_deadline(
        message=message,
        conversation_id=conversation_id,
        memory_service=memory,
        limit=limit,
        timeout_seconds=CITATION_COLLECTION_TIMEOUT_SECONDS,
        collector=collect_chat_citations,
    )


async def _finalize_and_persist_turn(
    *,
    service: ChatService,
    result: dict[str, Any],
    payload: ChatMessageRequest,
    role: ModelRole,
    user_id: str,
    project_id: str | None,
    identity_source: str,
    pending_action_id: int | None,
) -> dict[str, Any]:
    understanding = result.get("understanding")
    pending_action_id, fallback_reason = maybe_create_fallback_pending_action(
        message=payload.message,
        assistant_response=str(result.get("response") or ""),
        conversation_id=str(result.get("conversation_id") or payload.conversation_id),
        user_id=user_id,
        existing_pending_action_id=pending_action_id,
        understanding=understanding if isinstance(understanding, dict) else None,
    )
    if (
        fallback_reason
        and isinstance(understanding, dict)
        and not understanding.get("confirmation_reason")
    ):
        understanding["confirmation_reason"] = fallback_reason

    delivery_status = str(result.get("delivery_status") or "completed")
    business_state_by_delivery = {
        "pending_knowledge_space": TurnBusinessState.PENDING_KNOWLEDGE_SPACE,
        "pending_study": TurnBusinessState.PENDING_STUDY,
        "running_study": TurnBusinessState.RUNNING_STUDY,
        "failed": TurnBusinessState.FAILED,
        "cancelled": TurnBusinessState.CANCELLED,
    }
    execution = TurnExecutionResult.from_payload(
        strategy=infer_turn_strategy(result),
        payload=result,
        default_role=role,
    )
    finalized = ChatTurnFinalizer().finalize(
        execution=execution,
        understanding=understanding if isinstance(understanding, dict) else None,
        pending_action_id=pending_action_id,
        confirmation_reason=(
            (understanding or {}).get("confirmation_reason")
            if isinstance(understanding, dict)
            else None
        ),
        business_state=business_state_by_delivery.get(
            delivery_status,
            TurnBusinessState.COMPLETED,
        ),
        delivery_status=delivery_status,
        failure_classification=result.get("failure_classification"),
    )
    finalized_payload = finalized.to_payload()
    saved_message = await service.persist_finalized_turn(
        conversation_id=payload.conversation_id,
        user_message=payload.message,
        result=finalized_payload,
        user_id=user_id,
        project_id=project_id,
        identity_source=identity_source,
    )
    finalized_payload["message_id"] = str(saved_message.get("id"))
    return finalized_payload


@router.post(  # type: ignore[untyped-decorator]
    "/start", response_model=ChatStartResponse, summary="Inicia uma nova conversa"
)
async def start_chat(
    request: ChatStartRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
) -> ChatStartResponse:
    ctx = resolve_authenticated_user_context(
        http, None, allow_anonymous_fallback=False, endpoint_label="/api/v1/chat/start"
    )
    if not ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=chat_http_error_detail(
                code="CHAT_AUTH_REQUIRED",
                message="Authentication required",
                category="authn",
                retryable=False,
                http_status=status.HTTP_401_UNAUTHORIZED,
            ),
        )
    conversation_id = await service.start_conversation_async(
        request.persona, ctx.user_id, actor_project_id(http) or request.project_id
    )
    return ChatStartResponse(conversation_id=conversation_id)


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Envia uma mensagem e recebe a resposta do LLM",
)  # type: ignore[untyped-decorator]
async def send_message(
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
    memory: MemoryService = Depends(get_memory_service),
    rest_runs: ChatRestRunService = Depends(get_chat_rest_run_service),
) -> ChatMessageResponse:
    ctx = resolve_authenticated_user_context(
        http, None, allow_anonymous_fallback=False, endpoint_label="/api/v1/chat/message"
    )
    if not ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=chat_http_error_detail(
                code="CHAT_AUTH_REQUIRED",
                message="Authentication required",
                category="authn",
                retryable=False,
                http_status=status.HTTP_401_UNAUTHORIZED,
            ),
    )
    user_id = ctx.user_id

    try:
        payload = ChatMessageRequest.model_validate(await http.json())
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

    project_id = actor_project_id(http) or payload.project_id
    try:
        if hasattr(service, "resolve_authorized_knowledge_space_id"):
            active_knowledge_space_id = await service.resolve_authorized_knowledge_space_id(
                conversation_id=payload.conversation_id,
                user_id=user_id,
                project_id=project_id,
                requested_knowledge_space_id=payload.knowledge_space_id,
            )
        else:
            active_knowledge_space_id = await asyncio.to_thread(
                service.resolve_active_knowledge_space_id,
                conversation_id=payload.conversation_id,
                user_id=user_id,
                requested_knowledge_space_id=payload.knowledge_space_id,
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
    if active_knowledge_space_id:
        role = ModelRole.ORCHESTRATOR
        route_applied = False
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
    attachment: ChatRestAttachment | None = None
    try:
        idempotency_key = validate_chat_rest_idempotency_key(
            http.headers.get("Idempotency-Key")
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=chat_http_error_detail(
                code="CHAT_INVALID_IDEMPOTENCY_KEY",
                message=str(exc),
                category="validation",
                retryable=False,
                http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
        ) from exc
    if idempotency_key is not None:
        fingerprint = chat_rest_request_fingerprint(
            {
                **payload.model_dump(),
                "owner_user_id": user_id,
                "project_id": project_id,
                "active_knowledge_space_id": active_knowledge_space_id,
                "selected_role": role.value,
            }
        )
        try:
            attachment = await asyncio.to_thread(
                rest_runs.attach,
                owner_user_id=user_id,
                conversation_id=payload.conversation_id,
                request_id=idempotency_key,
                request_fingerprint=fingerprint,
            )
        except ChatRestIdempotencyConflict as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=chat_http_error_detail(
                    code="CHAT_IDEMPOTENCY_CONFLICT",
                    message=str(exc),
                    category="conflict",
                    retryable=False,
                    http_status=status.HTTP_409_CONFLICT,
                ),
            ) from exc
        except ChatRestRequestInProgress as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=chat_http_error_detail(
                    code="CHAT_REQUEST_IN_PROGRESS",
                    message=str(exc),
                    category="conflict",
                    retryable=True,
                    http_status=status.HTTP_409_CONFLICT,
                ),
            ) from exc
        if attachment.replay_result is not None:
            return cast(
                ChatMessageResponse,
                ChatMessageResponse(**attachment.replay_result),
            )
    try:
        result: dict[str, Any] = await service.send_message(
            conversation_id=payload.conversation_id,
            message=payload.message,
            role=role,
            priority=priority,
            timeout_seconds=payload.timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            knowledge_space_id=active_knowledge_space_id,
            identity_source=ctx.identity_source,
            requested_role=payload.role,
            routing_decision=routing_decision,
            route_applied=route_applied,
            defer_finalization=True,
        )
    except ConversationNotFoundError:
        if attachment is not None:
            await asyncio.to_thread(
                rest_runs.fail,
                attachment=attachment,
                error_code="CHAT_CONVERSATION_NOT_FOUND",
            )
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
        if attachment is not None:
            await asyncio.to_thread(
                rest_runs.fail,
                attachment=attachment,
                error_code="CHAT_MESSAGE_TOO_LARGE",
            )
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
        if attachment is not None:
            await asyncio.to_thread(
                rest_runs.fail,
                attachment=attachment,
                error_code="CHAT_INVOCATION_ERROR",
            )
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

    citations = result.get("citations")
    citation_status = result.get("citation_status")
    if not isinstance(citations, list) or not isinstance(citation_status, dict):
        citation_lookup_required = requires_mandatory_citations(
            payload.message
        ) or references_uploaded_material(payload.message)
        if citation_lookup_required:
            try:
                citation_result = await _collect_chat_citations_with_deadline(
                    message=payload.message,
                    conversation_id=str(result.get("conversation_id") or payload.conversation_id),
                    memory=memory,
                    limit=5,
                )
                citations = citation_result.get("citations") or []
                citations_retrieval_failed = bool(citation_result.get("retrieval_failed"))
                citations_failure_classification = citation_result.get(
                    "failure_classification"
                )
                citations_failure_reason = citation_result.get("retrieval_failure_reason")
            except asyncio.TimeoutError:
                logger.warning(
                    "chat_message_citations_timeout",
                    conversation_id=payload.conversation_id,
                    timeout_seconds=CITATION_COLLECTION_TIMEOUT_SECONDS,
                )
                citations = []
                citations_retrieval_failed = True
                citations_failure_classification = "citation_timeout"
                citations_failure_reason = "retrieval_timeout"
            except Exception as e:
                logger.warning("chat_message_citations_failed", error=str(e))
                citations = []
                citations_retrieval_failed = True
                citations_failure_classification = "citation_unavailable"
                citations_failure_reason = "retrieval_error"
        else:
            citations = []
            citations_retrieval_failed = False
            citations_failure_classification = None
            citations_failure_reason = None
            logger.debug(
                "chat_message_optional_citations_skipped",
                conversation_id=payload.conversation_id,
            )
        citation_status = build_citation_status(
            message=payload.message,
            citations=citations,
            retrieval_failed=citations_retrieval_failed,
            retrieval_failure_reason=citations_failure_reason,
        )
        if citations_failure_classification:
            result["failure_classification"] = citations_failure_classification
    result["citations"] = citations
    result["citation_status"] = citation_status
    pending_action_id = None
    try:
        if result.get("pending_action_id") is not None:
            pending_action_id = _required_int(
                result.get("pending_action_id"), field_name="pending_action_id"
            )
    except Exception:
        pending_action_id = None
    if pending_action_id is None:
        pending_action_id = extract_pending_action_id_from_text(str(result.get("response") or ""))

    understanding = result.get("understanding")
    if isinstance(understanding, dict):
        raw_confidence = understanding.get("confidence")
        try:
            confidence = _bounded_confidence(raw_confidence)
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

    needs_study_job = False
    if result.get("citation_status", {}).get("status") == "missing_required":
        if active_knowledge_space_id:
            result["study_job"] = None
            result["source_scope"] = result.get("source_scope") or {
                "knowledge_space_id": active_knowledge_space_id
            }
        else:
            needs_study_job = True

        result.update(
            build_missing_citation_resolution(
                active_knowledge_space_id=active_knowledge_space_id,
                retrieval_reason=result.get("citation_status", {}).get("reason"),
            )
        )

    if routing_decision:
        result["understanding"] = build_routed_understanding(
            result.get("understanding")
            if isinstance(result.get("understanding"), dict)
            else None,
            routing_decision=routing_decision,
            requested_role=payload.role,
            selected_role=role,
            route_applied=route_applied,
            requires_confirmation=routing_decision.risk_level == "high",
            confirmation_reason="high_risk",
        )

    try:
        result = await _finalize_and_persist_turn(
            service=service,
            result=result,
            payload=payload,
            role=role,
            user_id=user_id,
            project_id=project_id,
            identity_source=ctx.identity_source,
            pending_action_id=pending_action_id,
        )
    except Exception:
        if attachment is not None:
            await asyncio.to_thread(
                rest_runs.fail,
                attachment=attachment,
                error_code="CHAT_FINALIZATION_ERROR",
            )
        raise

    if needs_study_job:
        try:
            jobs = _get_chat_study_job_service(http, service)
            job = await asyncio.to_thread(
                jobs.create_job,
                conversation_id=payload.conversation_id,
                message_id=str(result["message_id"]),
                question=payload.message,
                user_id=user_id,
                placeholder_message=str(result.get("study_notice") or result["response"]),
            )
            result["study_job"] = {
                "job_id": job.job_id,
                "status": job.status,
                "poll_url": f"/api/v1/chat/study-jobs/{job.job_id}",
                "conversation_id": payload.conversation_id,
                "message_id": str(result["message_id"]),
                "placeholder_message": job.placeholder_message,
            }
            asyncio.create_task(
                jobs.run_job(job_id=job.job_id, role=role, priority=priority)
            )
        except Exception as e:
            logger.warning(
                "chat_message_start_study_failed",
                conversation_id=payload.conversation_id,
                error=str(e),
            )

    if attachment is not None:
        await asyncio.to_thread(
            rest_runs.complete,
            attachment=attachment,
            result=result,
        )

    return cast(ChatMessageResponse, ChatMessageResponse(**result))
