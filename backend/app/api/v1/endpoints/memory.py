import structlog
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.memory.generative_memory import generative_memory_service
from app.core.security.request_guard import resolve_user_scope_id
from app.db.vector_store import (
    aget_or_create_collection,
    build_user_chat_collection_name,
    build_user_docs_collection_name,
    build_user_memory_collection_name,
    get_async_qdrant_client,
)
from app.models.schemas import Experience, ScoredExperience
from app.services.memory_service import MemoryService, get_memory_service
from app.services.secret_memory_service import secret_memory_service
from app.services.user_preference_memory_service import user_preference_memory_service

router = APIRouter()
logger = structlog.get_logger(__name__)


class MemoryTimelineItem(BaseModel):
    content: str
    ts_ms: int | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None
    composite_id: str | None = None
    memory_class: str | None = None
    retention_policy: str | None = None
    recall_policy: str | None = None
    sensitivity: str | None = None
    stability_score: float | None = None
    scope: str | None = None


class UserPreferenceMemoryItem(BaseModel):
    id: str | None = None
    content: str
    ts_ms: int | None = None
    preference_kind: str | None = None
    instruction_text: str | None = None
    scope: str | None = None
    confidence: float | None = None
    user_id: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    active: bool = True
    origin: str | None = None
    dedupe_key: str | None = None
    memory_class: str | None = None
    retention_policy: str | None = None
    recall_policy: str | None = None
    sensitivity: str | None = None
    stability_score: float | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None


class SecretMemoryCreateRequest(BaseModel):
    label: str
    value: str
    secret_type: str | None = None
    secret_scope: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None


class SecretMemoryItem(BaseModel):
    id: str | None = None
    ts_ms: int | None = None
    secret_label: str
    secret_type: str | None = None
    secret_scope: str | None = None
    masked_value: str | None = None
    active: bool = True
    conversation_id: str | None = None
    memory_class: str | None = None
    retention_policy: str | None = None
    recall_policy: str | None = None
    sensitivity: str | None = None
    stability_score: float | None = None
    metadata: dict[str, Any] | None = None


def _parse_iso_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def _coerce_ts_ms(value: Any | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        return _parse_iso_to_ms(value)
    return None


def _experience_to_item(exp: ScoredExperience) -> MemoryTimelineItem:
    meta = exp.metadata or {}
    meta_dict = meta if isinstance(meta, dict) else meta.model_dump()
    ts_ms = (
        _coerce_ts_ms(getattr(meta, "ts_ms", None))
        or _coerce_ts_ms(meta_dict.get("ts_ms"))
        or _coerce_ts_ms(meta_dict.get("timestamp"))
        or _parse_iso_to_ms(exp.timestamp)
    )
    return MemoryTimelineItem(
        content=exp.content,
        ts_ms=ts_ms,
        metadata=meta_dict,
        score=exp.score,
        memory_class=meta_dict.get("memory_class"),
        retention_policy=meta_dict.get("retention_policy"),
        recall_policy=meta_dict.get("recall_policy"),
        sensitivity=meta_dict.get("sensitivity"),
        stability_score=meta_dict.get("stability_score"),
        scope=meta_dict.get("scope"),
    )


def _point_to_item(point: Any) -> MemoryTimelineItem:
    payload = getattr(point, "payload", None) or {}
    meta = payload.get("metadata") or {}
    ts_ms = _coerce_ts_ms(payload.get("ts_ms")) or _coerce_ts_ms(meta.get("timestamp"))
    return MemoryTimelineItem(
        content=payload.get("content", ""),
        ts_ms=ts_ms,
        metadata=meta,
        score=getattr(point, "score", None),
        composite_id=payload.get("composite_id"),
        memory_class=meta.get("memory_class"),
        retention_policy=meta.get("retention_policy"),
        recall_policy=meta.get("recall_policy"),
        sensitivity=meta.get("sensitivity"),
        stability_score=meta.get("stability_score"),
        scope=meta.get("scope"),
    )


def _timeline_user_collections(user_id: str) -> list[str]:
    return [
        build_user_memory_collection_name(user_id),
        build_user_chat_collection_name(user_id),
        build_user_docs_collection_name(user_id),
    ]


async def _load_user_timeline_points(
    *,
    user_id: str,
    query: str | None,
    start_ts: int | None,
    end_ts: int | None,
    limit: int,
) -> list[Any]:
    client = get_async_qdrant_client()
    vector = await aembed_text(query) if query else None
    points: list[Any] = []
    for collection_name in _timeline_user_collections(user_id):
        coll = await aget_or_create_collection(collection_name)
        must: list[models.FieldCondition] = []
        if start_ts is not None or end_ts is not None:
            rng = models.Range(gte=start_ts, lte=end_ts)
            must.append(models.FieldCondition(key="metadata.timestamp", range=rng))
        qfilter = models.Filter(must=must) if must else None
        if vector is not None:
            res = await client.query_points(
                collection_name=coll,
                query=vector,
                limit=limit,
                with_payload=True,
                query_filter=qfilter,
            )
            coll_points = list(getattr(res, "points", res) or [])
        else:
            coll_points, _ = await client.scroll(
                collection_name=coll,
                scroll_filter=qfilter,
                limit=limit,
                with_payload=True,
            )
        points.extend(coll_points)
    return points


def _sort_and_dedupe_timeline(items: list[MemoryTimelineItem], limit: int) -> list[MemoryTimelineItem]:
    deduped: dict[str, MemoryTimelineItem] = {}
    for item in items:
        key = str(
            item.composite_id
            or (item.metadata or {}).get("dedupe_key")
            or (item.metadata or {}).get("doc_id")
            or f"{item.content}:{item.ts_ms}"
        )
        current = deduped.get(key)
        if current is None or int(item.ts_ms or 0) > int(current.ts_ms or 0):
            deduped[key] = item
    ordered = sorted(deduped.values(), key=lambda item: item.ts_ms or 0, reverse=True)
    return ordered[:limit]


@router.get("/timeline", response_model=list[MemoryTimelineItem])
async def get_memories_timeline(
    request: Request,
    start_date: str | None = Query(None, description="Start date (ISO 8601), inclusive"),
    end_date: str | None = Query(None, description="End date (ISO 8601), inclusive"),
    query: str | None = Query(None, description="Semantic text query to filter memories"),
    limit: int = Query(10, ge=1, le=100),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
    user_id: str | None = Query(None, description="User ID for active memory scope"),
    service: MemoryService = Depends(get_memory_service),
):
    """
    Retrieves memories within a specific timeframe ("Time Travel").
    Allows semantic filtering via `query`.
    """
    start_ts: int | None = None
    end_ts: int | None = None

    try:
        if start_date:
            dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            start_ts = int(dt.timestamp() * 1000)
        if end_date:
            dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            end_ts = int(dt.timestamp() * 1000)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use ISO 8601 (e.g., 2023-01-01T12:00:00Z). Error: {e}",
        )

    resolved_user_id = resolve_user_scope_id(request, user_id)

    if resolved_user_id:
        try:
            fetch_limit = min(500, max(limit * 5, limit))
            points = await _load_user_timeline_points(
                user_id=str(resolved_user_id),
                query=query,
                start_ts=start_ts,
                end_ts=end_ts,
                limit=fetch_limit,
            )
            return _sort_and_dedupe_timeline([_point_to_item(p) for p in points], limit)
        except Exception as e:
            logger.error("log_error", message=f"Error retrieving user timeline: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user timeline memories",
            )

    try:
        memories = await service.recall_by_timeframe(
            query=query, start_ts_ms=start_ts, end_ts_ms=end_ts, limit=limit, min_score=min_score
        )
        return [_experience_to_item(exp) for exp in memories]
    except Exception as e:
        logger.error("log_error", message=f"Error retrieving timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve timeline memories",
        )

@router.get("/generative", response_model=list[ScoredExperience])
async def get_generative_memories(
    request: Request,
    query: str = Query(..., description="Query for memory retrieval"),
    limit: int = Query(10, ge=1, le=100),
    type: str | None = Query(None, description="Filter by memory type (episodic|semantic|procedural)"),
    user_id: str | None = Query(None, description="Filter by user_id"),
    conversation_id: str | None = Query(None, description="Filter by conversation_id"),
):
    """
    Retrieves memories using the Generative Agents scoring (Recency * Importance * Relevance).
    """
    try:
        resolved_user_id = resolve_user_scope_id(request, user_id)
        resolved_conversation_id = (
            conversation_id
            or request.headers.get("X-Conversation-Id")
            or request.headers.get("X-Session-Id")
        )
        memories = await generative_memory_service.retrieve_memories(
            query,
            limit=limit,
            type_filter=type,
            user_id=resolved_user_id,
            conversation_id=resolved_conversation_id,
        )
        return memories
    except Exception as e:
        logger.error("log_error", message=f"Error retrieving generative memories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve generative memories: {e}"
        )

@router.post("/generative", response_model=Experience)
async def add_generative_memory(
    request: Request,
    content: str,
    importance: float | None = Query(None, ge=0.0, le=10.0),
    type: str = "episodic",
    user_id: str | None = Query(None, description="User ID for user-scoped memory mirrors"),
    conversation_id: str | None = Query(None, description="Conversation ID to bind memory"),
    session_id: str | None = Query(None, description="Session ID alias (defaults to conversation_id)"),
):
    """
    Adds a memory to the Generative Stream (calculates importance if missing).
    """
    try:
        meta = {}
        if importance is not None:
            meta["importance"] = importance
        resolved_user_id = resolve_user_scope_id(request, user_id)
        resolved_conversation_id = (
            conversation_id or request.headers.get("X-Conversation-Id") or request.headers.get("X-Session-Id")
        )
        resolved_session_id = session_id or request.headers.get("X-Session-Id") or resolved_conversation_id
        if resolved_user_id:
            meta["user_id"] = str(resolved_user_id)
        if resolved_conversation_id:
            meta["conversation_id"] = str(resolved_conversation_id)
        if resolved_session_id:
            meta["session_id"] = str(resolved_session_id)
        meta["origin"] = str(meta.get("origin") or "frontend.generative_memory_panel")

        memory = await generative_memory_service.add_memory(content, type=type, metadata=meta)
        return memory
    except Exception as e:
        logger.error("log_error", message=f"Error adding generative memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add generative memory: {e}"
        )


@router.get("/preferences", response_model=list[UserPreferenceMemoryItem])
async def get_user_preferences(
    request: Request,
    user_id: str | None = Query(None, description="User ID"),
    conversation_id: str | None = Query(None, description="Optional conversation filter"),
    query: str | None = Query(None, description="Optional semantic query"),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
):
    resolved_user_id = resolve_user_scope_id(request, user_id)
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required (query param or authenticated actor)",
        )
    try:
        items = await user_preference_memory_service.list_preferences(
            user_id=str(resolved_user_id),
            conversation_id=conversation_id,
            query=query,
            limit=limit,
            active_only=active_only,
        )
        return [UserPreferenceMemoryItem(**item) for item in items]
    except Exception as exc:
        logger.error("log_error", message=f"Error listing user preferences: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences",
        )


@router.get("/secrets", response_model=list[SecretMemoryItem])
async def get_user_secrets(
    request: Request,
    user_id: str | None = Query(None, description="User ID"),
    conversation_id: str | None = Query(None, description="Optional conversation filter"),
    query: str | None = Query(None, description="Optional semantic query"),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
):
    resolved_user_id = resolve_user_scope_id(request, user_id)
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required (query param or authenticated actor)",
        )
    try:
        items = await secret_memory_service.list_secrets(
            user_id=str(resolved_user_id),
            conversation_id=conversation_id,
            query=query,
            limit=limit,
            active_only=active_only,
            reveal=False,
        )
        return [SecretMemoryItem(**item) for item in items]
    except Exception as exc:
        logger.error("log_error", message=f"Error listing user secrets: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user secrets",
        )


@router.post("/secrets", response_model=SecretMemoryItem, status_code=status.HTTP_201_CREATED)
async def add_user_secret(
    request: Request,
    body: SecretMemoryCreateRequest,
):
    resolved_user_id = resolve_user_scope_id(request, body.user_id)
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required (body or authenticated actor)",
        )
    try:
        stored = await secret_memory_service.store_secret(
            user_id=str(resolved_user_id),
            label=body.label,
            value=body.value,
            secret_type=body.secret_type or secret_memory_service._infer_secret_type(body.label),
            secret_scope=body.secret_scope,
            conversation_id=body.conversation_id,
            source="memory.secret_api",
        )
        item = {
            **stored,
            "memory_class": "secret",
            "retention_policy": "persistent",
            "recall_policy": "explicit_only",
            "sensitivity": "secret",
            "stability_score": 0.98,
            "active": True,
            "conversation_id": body.conversation_id,
            "metadata": {
                "memory_class": "secret",
                "retention_policy": "persistent",
                "recall_policy": "explicit_only",
                "sensitivity": "secret",
                "stability_score": 0.98,
            },
        }
        return SecretMemoryItem(**item)
    except Exception as exc:
        logger.error("log_error", message=f"Error storing user secret: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store user secret",
        )
