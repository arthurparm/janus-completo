import asyncio
import hashlib
import os
import re
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.llm import ModelPriority, ModelRole
from app.core.ui.generative_ui import extract_ui_block
from app.services.chat_service import (
    ChatService,
    ChatServiceError,
    ConversationNotFoundError,
    MessageTooLargeError,
    get_chat_service,
)
from app.services.memory_service import MemoryService, get_memory_service
from app.services.trace_service import TraceService, get_trace_service

router = APIRouter(tags=["Chat"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---


class ChatStartRequest(BaseModel):
    persona: str | None = Field(None)
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)
    title: str | None = Field(None)


class ChatStartResponse(BaseModel):
    conversation_id: str


class ChatMessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    role: str = Field("orchestrator")
    priority: str = Field("fast_and_cheap")
    timeout_seconds: int | None = None
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)


class ChatMessageResponse(BaseModel):
    response: str
    provider: str
    model: str
    role: str
    conversation_id: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    ui: dict[str, Any] | None = None
    understanding: dict[str, Any] | None = None


class ChatMessage(BaseModel):
    timestamp: float
    role: str
    text: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    ui: dict[str, Any] | None = None
    understanding: dict[str, Any] | None = None


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    persona: str | None
    messages: list[ChatMessage]


class ChatHistoryPaginatedResponse(BaseModel):
    conversation_id: str
    persona: str | None
    messages: list[ChatMessage]
    total_count: int
    has_more: bool
    next_offset: int | None
    limit: int
    offset: int


class ChatRenameRequest(BaseModel):
    new_title: str = Field(..., min_length=1)
    user_id: str | None = Field(None)
    project_id: str | None = Field(None)


class ChatListResponse(BaseModel):
    conversation_id: str
    title: str | None
    created_at: float | None
    updated_at: float | None
    last_message: ChatMessage | None
    message_count: int | None = None
    tags: list[str] = Field(default_factory=list)
    last_message_at: str | None = None


def _apply_ui_to_message(message: dict[str, Any]) -> dict[str, Any]:
    text = message.get("text", "")
    clean_text, ui = extract_ui_block(text)
    payload = dict(message)
    payload["text"] = clean_text
    if ui:
        payload["ui"] = ui
    return payload


def _actor_user_id(http: Request | None) -> str | None:
    if http is None:
        return None
    try:
        actor = getattr(http.state, "actor_user_id", None)
        return str(actor) if actor else None
    except Exception:
        return None


def _anonymous_user_id(http: Request | None) -> str | None:
    if http is None:
        return None
    try:
        client_ip = (
            (http.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            or (http.client.host if http.client else "")
        )
        ua = http.headers.get("user-agent") or "unknown"
        if not client_ip:
            return None
        digest = hashlib.sha256(f"{client_ip}|{ua}".encode("utf-8")).hexdigest()[:16]
        return f"anon:{digest}"
    except Exception:
        return None


def _resolve_user_id(http: Request | None, explicit_user_id: str | None) -> str | None:
    return explicit_user_id or _actor_user_id(http) or _anonymous_user_id(http)


def _ensure_origin_allowed(http: Request | None) -> None:
    if http is None:
        return
    try:
        from app.config import settings as _settings
    except Exception:
        _settings = None

    origin = (http.headers.get("origin") or "").lower()
    allowed_origins = []
    try:
        allowed_origins = list(getattr(_settings, "CORS_ALLOW_ORIGINS", [])) or []
    except Exception:
        allowed_origins = []
    if allowed_origins and origin and origin not in [o.lower() for o in allowed_origins]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")


_CITATION_REQUIRED_PATTERNS = (
    r"\bcodigo\b",
    r"\bcode\b",
    r"\bfuncao\b",
    r"\bfunction\b",
    r"\bclasse\b",
    r"\bclass\b",
    r"\barquivo\b",
    r"\bfile\b",
    r"\bdocumentacao\b",
    r"\bdocumentation\b",
    r"\bdocs?\b",
    r"\breadme\b",
    r"\bapi\b",
    r"\bendpoint\b",
    r"\.py\b",
    r"\.ts\b",
    r"\.js\b",
)


def _requires_mandatory_citations(message: str) -> bool:
    text = (message or "").lower()
    return any(re.search(pattern, text) for pattern in _CITATION_REQUIRED_PATTERNS)


def _confidence_confirmation_threshold() -> float:
    raw = os.getenv("CHAT_CONFIDENCE_CONFIRMATION_THRESHOLD", "0.65").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.65


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"


# --- Endpoints ---


@router.post("/start", response_model=ChatStartResponse, summary="Inicia uma nova conversa")
async def start_chat(
    request: ChatStartRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    user_id = _resolve_user_id(http, request.user_id)
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
    try:
        role = ModelRole(payload.role)
        priority = ModelPriority(payload.priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role or priority"
        )

    user_id = _resolve_user_id(http, payload.user_id)
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

    # Build citations via vector search on user documents/chat
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
        for r in vec_results:
            meta = r.get("metadata") or {}
            content = (
                r.get("content") or r.get("payload", {}).get("content") or r.get("page_content")
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
                    "id": r.get("id"),
                    "title": meta.get("title"),
                    "url": meta.get("url"),
                    "doc_id": meta.get("doc_id"),
                    "file_path": meta.get("file_path"),
                    "type": meta.get("type"),
                    "origin": meta.get("origin"),
                    "line_start": line_start,
                    "line_end": line_end,
                    "line": line_start,
                    "score": r.get("score"),
                    "snippet": content,
                }
            )
    except Exception as e:
        logger.warning(f"Failed to retrieve citations for message: {e}")
        citations = []
    result["citations"] = citations

    understanding = result.get("understanding")
    if isinstance(understanding, dict):
        raw_confidence = understanding.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(raw_confidence)))
        except Exception:
            confidence = 0.0
        threshold = _confidence_confirmation_threshold()
        low_confidence = confidence < threshold
        intent = str(understanding.get("intent") or "")
        requires_confirmation = bool(understanding.get("requires_confirmation"))
        understanding["confidence"] = round(confidence, 2)
        understanding["confidence_band"] = _confidence_band(confidence)
        understanding["low_confidence"] = low_confidence
        if low_confidence and (requires_confirmation or intent in {"action_request", "reminder"}):
            understanding["requires_confirmation"] = True
            understanding["confirmation_reason"] = "low_confidence"
            result["response"] = (
                f"Estou com baixa confianca ({int(round(confidence * 100))}%). "
                "Antes de executar essa acao, confirme se devo prosseguir."
            )

    if _requires_mandatory_citations(payload.message) and not citations:
        result["response"] = (
            "Nao encontrei citacoes rastreaveis para essa resposta de documento/codigo. "
            "Envie mais contexto (arquivo, funcao ou documento) para eu responder com fonte."
        )

    return ChatMessageResponse(**result)


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
    """
    Retorna o histórico da conversa.
    Se limit for especificado, usa paginação com validação de acesso.
    Caso contrário, retorna todo o histórico (modo legado).
    """
    logger.info(
        f"API request for chat history: {conversation_id}, limit: {limit}, offset: {offset}"
    )

    try:
        # Obter user_id do header para validação RBAC
        try:
            user_id = getattr(http.state, "actor_user_id", None) if http else None
        except Exception:
            user_id = None

        # Obter project_id do header se disponível
        try:
            project_id = getattr(http.state, "actor_project_id", None) if http else None
        except Exception:
            project_id = None

        # Se limit for especificado, usar modo paginado com RBAC
        if limit is not None:
            # Usar método paginado com validação de acesso
            hist = service.get_history_paginated(
                conversation_id=conversation_id,
                limit=limit,
                offset=offset,
                before_ts=before_ts,
                after_ts=after_ts,
                user_id=user_id,
                project_id=project_id,
            )

            logger.info(
                f"Retrieved paginated history for conversation {conversation_id}: "
                f"{len(hist.get('messages', []))} messages (total: {hist.get('total_count', 0)})"
            )

            # Converter mensagens para DTOs
            messages = []
            for i, m in enumerate(hist.get("messages", [])):
                try:
                    if isinstance(m, dict) and "timestamp" in m and "role" in m and "text" in m:
                        messages.append(ChatMessage(**_apply_ui_to_message(m)))
                    else:
                        logger.warning(f"Skipping invalid message at index {i}: {m}")
                except Exception as e:
                    logger.warning(f"Error converting message at index {i}: {e}")

            logger.info(
                f"Successfully converted {len(messages)} valid messages for conversation {conversation_id}"
            )

            # Retornar resposta no formato legado (sem metadados de paginação)
            return ChatHistoryResponse(
                conversation_id=hist["conversation_id"],
                persona=hist.get("persona"),
                messages=messages,
            )

        else:
            # Modo legado - retorna todo o histórico com RBAC quando disponível
            hist = service.get_history(
                conversation_id, user_id=user_id, project_id=project_id
            )
            logger.info(
                f"Retrieved full history for conversation {conversation_id} with {len(hist.get('messages', []))} messages"
            )

            # Convert dict messages to DTOs with error handling
            messages = []
            for i, m in enumerate(hist.get("messages", [])):
                try:
                    if isinstance(m, dict) and "timestamp" in m and "role" in m and "text" in m:
                        messages.append(ChatMessage(**_apply_ui_to_message(m)))
                    else:
                        logger.warning(f"Skipping invalid message at index {i}: {m}")
                except Exception as e:
                    logger.warning(f"Error converting message at index {i}: {e}")

            logger.info(
                f"Successfully converted {len(messages)} valid messages for conversation {conversation_id}"
            )
            return ChatHistoryResponse(
                conversation_id=hist["conversation_id"],
                persona=hist.get("persona"),
                messages=messages,
            )

    except ConversationNotFoundError:
        logger.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError as e:
        if "Access denied" in str(e):
            logger.warning(f"Access denied for conversation {conversation_id}: {e}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        logger.error(f"Chat service error for conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error getting history for conversation {conversation_id}: {e}",
            exc_info=True,
        )
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
    """
    Retorna histórico de mensagens com paginação e validação de acesso.

    - **limit**: Número máximo de mensagens (1-200, padrão 50)
    - **offset**: Número de mensagens a pular (padrão 0)
    - **before_ts**: Timestamp para buscar mensagens antes desta data
    - **after_ts**: Timestamp para buscar mensagens após esta data
    """
    logger.info(
        f"API request for paginated chat history: {conversation_id}, limit: {limit}, offset: {offset}"
    )

    try:
        # Obter user_id do header para validação RBAC
        try:
            user_id = getattr(http.state, "actor_user_id", None) if http else None
        except Exception:
            user_id = None

        # Obter project_id do header se disponível
        try:
            project_id = getattr(http.state, "actor_project_id", None) if http else None
        except Exception:
            project_id = None

        # Usar método paginado com validação de acesso
        hist = service.get_history_paginated(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            before_ts=before_ts,
            after_ts=after_ts,
            user_id=user_id,
            project_id=project_id,
        )

        logger.info(
            f"Retrieved paginated history for conversation {conversation_id}: "
            f"{len(hist.get('messages', []))} messages (total: {hist.get('total_count', 0)})"
        )

        # Converter mensagens para DTOs
        messages = []
        for i, m in enumerate(hist.get("messages", [])):
            try:
                if isinstance(m, dict) and "timestamp" in m and "role" in m and "text" in m:
                    messages.append(ChatMessage(**_apply_ui_to_message(m)))
                else:
                    logger.warning(f"Skipping invalid message at index {i}: {m}")
            except Exception as e:
                logger.warning(f"Error converting message at index {i}: {e}")

        logger.info(
            f"Successfully converted {len(messages)} valid messages for conversation {conversation_id}"
        )

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
        logger.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    except ChatServiceError as e:
        if "Access denied" in str(e):
            logger.warning(
                f"Access denied for user {user_id} to conversation {conversation_id}: {e}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        logger.error(f"Chat service error for conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error getting paginated history for conversation {conversation_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/conversations",
    response_model=list[ChatListResponse],
    summary="Lista conversas com filtros de RBAC",
)
async def list_conversations(
    user_id: str | None = None,
    project_id: str | None = None,
    limit: int = 50,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        hdr_uid = getattr(http.state, "actor_user_id", None) if http else None
    except Exception:
        hdr_uid = None

    final_user_id = user_id or hdr_uid

    items = await service.list_conversations(
        user_id=final_user_id, project_id=project_id, limit=limit
    )

    # map items to DTOs
    def map_item(it: dict[str, Any]) -> ChatListResponse:
        last = it.get("last_message")
        last_msg = ChatMessage(**_apply_ui_to_message(last)) if isinstance(last, dict) else None
        return ChatListResponse(
            conversation_id=it.get("conversation_id"),
            title=it.get("title"),
            created_at=it.get("created_at"),
            updated_at=it.get("updated_at"),
            last_message=last_msg,
        )

    conversations = [map_item(it) for it in items]

    # Return as list (FastAPI expects List[ChatListResponse])
    return conversations


@router.put("/{conversation_id}/rename", summary="Renomeia uma conversa")
async def rename_conversation(
    conversation_id: str,
    payload: ChatRenameRequest,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        hdr_uid = None
        try:
            hdr_uid = getattr(http.state, "actor_user_id", None) if http else None
        except Exception:
            hdr_uid = None
        await service.rename_conversation(
            conversation_id,
            payload.new_title,
            user_id=payload.user_id or hdr_uid,
            project_id=payload.project_id,
        )
        return {"status": "ok"}
    except ChatServiceError as e:
        logger.warning("Access denied renaming conversation", conversation_id=conversation_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/health", summary="Verifica o status do serviço de chat")
async def chat_health(service: ChatService = Depends(get_chat_service)):
    """Verifica se o serviço de chat está funcionando corretamente."""
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
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chat service unhealthy")


@router.delete("/{conversation_id}", summary="Apaga uma conversa")
async def delete_conversation(
    conversation_id: str,
    user_id: str | None = None,
    project_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    try:
        hdr_uid = None
        try:
            hdr_uid = getattr(http.state, "actor_user_id", None) if http else None
        except Exception:
            hdr_uid = None
        await service.delete_conversation(
            conversation_id, user_id=user_id or hdr_uid, project_id=project_id
        )
        return {"status": "ok"}
    except ChatServiceError as e:
        logger.warning("Access denied deleting conversation", conversation_id=conversation_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/stream/{conversation_id}", summary="Streaming de resposta via SSE")
async def stream_message(
    conversation_id: str,
    message: str,
    role: str = "orchestrator",
    priority: str = "fast_and_cheap",
    timeout_seconds: int | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    """SSE de respostas do LLM.
    Protocolo atual: 2025-11.v1.
    Eventos: protocol, ack, token, partial (compat), heartbeat, done, error.
    Descontinuação de partial: ver env CHAT_SSE_PARTIAL_DEPRECATE_AT.
    """
    # valida enum
    try:
        role_enum = ModelRole(role)
        priority_enum = ModelPriority(priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role or priority"
        )

    # Valida origem (CORS) para SSE
    _ensure_origin_allowed(http)

    # Limita tamanho máximo da mensagem (10KB)
    if message:
        try:
            message_size = len(message.encode("utf-8"))
        except Exception:
            message_size = len(message)
        if message_size > 10 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Message too large"
            )

    try:
        if not user_id:
            try:
                user_id = getattr(http.state, "actor_user_id", None) if http else None
            except Exception:
                user_id = None
        if not project_id:
            try:
                project_id = getattr(http.state, "actor_project_id", None) if http else None
            except Exception:
                project_id = None

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
    return StreamingResponse(gen, media_type="text/event-stream", headers=headers)


@router.get(
    "/{conversation_id}/trace", summary="Retorna o rastro de execução (Chain of Thought)"
)
async def get_conversation_trace(
    conversation_id: str,
    service: TraceService = Depends(get_trace_service),
):
    """
    Retorna o histórico de execução (Chain of Thought) dos agentes para uma conversa.
    Os eventos são estruturados em 'steps' contendo timestamp, agente, ação e conteúdo.
    """
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
    """
    Endpoint SSE dedicado para observar eventos de agentes em tempo real.
    Conecta na fila de eventos do RabbitMQ e retorna 'AgentThinking', 'AgentAction', etc.
    """
    # Valida origem (CORS) para SSE
    _ensure_origin_allowed(http)

    try:
        # Recupera user_id do header se não passado
        if not user_id:
            try:
                user_id = getattr(http.state, "actor_user_id", None) if http else None
            except Exception:
                pass

        gen = service.stream_events(conversation_id=conversation_id, user_id=user_id)
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
    return StreamingResponse(gen, media_type="text/event-stream", headers=headers)
