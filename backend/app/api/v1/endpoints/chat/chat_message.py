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

from .deps import resolve_user_id
from .models import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
)
from .policies import confidence_band, confidence_confirmation_threshold, requires_mandatory_citations

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/start", response_model=ChatStartResponse, summary="Inicia uma nova conversa")
async def start_chat(
    request: ChatStartRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    user_id = resolve_user_id(http, request.user_id)
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid role or priority"
        )

    user_id = resolve_user_id(http, payload.user_id)
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
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except MessageTooLargeError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e)
        )
    except ChatServiceError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        logger.error("ChatServiceError on /chat/message", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )

    citations: list[dict[str, Any]] = []
    try:
        filters: dict[str, Any] = {"status_not": "duplicate"}
        if result.get("conversation_id"):
            filters["metadata.session_id"] = result.get("conversation_id")
        if user_id:
            filters["metadata.user_id"] = str(user_id)
        vec_results = await memory.recall_filtered(
            query=payload.message, filters=filters, limit=5, min_score=0.1
        )
        for item in vec_results:
            meta = item.get("metadata") or {}
            content = (
                item.get("content") or item.get("payload", {}).get("content") or item.get("page_content")
            )
            line_start = (
                meta.get("line_start")
                or meta.get("start_line")
                or meta.get("line")
                or meta.get("line_no")
            )
            line_end = meta.get("line_end") or meta.get("end_line")
            citations.append(
                {
                    "id": item.get("id"),
                    "title": meta.get("title"),
                    "url": meta.get("url"),
                    "doc_id": meta.get("doc_id"),
                    "file_path": meta.get("file_path"),
                    "type": meta.get("type"),
                    "origin": meta.get("origin"),
                    "line_start": line_start,
                    "line_end": line_end,
                    "line": line_start,
                    "score": item.get("score"),
                    "snippet": content,
                }
            )
    except Exception as e:
        logger.warning("log_warning", message=f"Failed to retrieve citations for message: {e}")
        citations = []
    result["citations"] = citations

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

    if requires_mandatory_citations(payload.message) and not citations:
        result["response"] = (
            "Nao encontrei citacoes rastreaveis para essa resposta de documento/codigo. "
            "Envie mais contexto (arquivo, funcao ou documento) para eu responder com fonte."
        )

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

    return ChatMessageResponse(**result)
