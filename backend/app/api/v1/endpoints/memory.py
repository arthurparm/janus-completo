from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from qdrant_client import models

from app.core.embeddings.embedding_manager import aembed_text
from app.core.memory.generative_memory import generative_memory_service
from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client
from app.models.schemas import Experience, ScoredExperience
from app.services.memory_service import MemoryService, get_memory_service
from app.services.user_preference_memory_service import user_preference_memory_service

router = APIRouter()
logger = structlog.get_logger(__name__)


class MemoryTimelineItem(BaseModel):
    content: str
    ts_ms: int | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None
    composite_id: str | None = None


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
    metadata: dict[str, Any] | None = None
    score: float | None = None


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
    )


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

    resolved_user_id = user_id or request.headers.get("X-User-Id")

    if resolved_user_id:
        try:
            collection_name = await aget_or_create_collection(f"user_{resolved_user_id}")
            client = get_async_qdrant_client()

            must: list[models.FieldCondition] = []
            if start_ts is not None or end_ts is not None:
                rng = models.Range(gte=start_ts, lte=end_ts)
                must.append(models.FieldCondition(key="metadata.timestamp", range=rng))

            qfilter = models.Filter(must=must) if must else None

            points: list[Any] = []
            if query:
                vec = await aembed_text(query)
                res = await client.query_points(
                    collection_name=collection_name,
                    query=vec,
                    limit=limit,
                    with_payload=True,
                    query_filter=qfilter,
                )
                points = getattr(res, "points", res) or []
            else:
                scroll_limit = min(500, max(limit * 5, limit))
                points, _ = await client.scroll(
                    collection_name=collection_name,
                    scroll_filter=qfilter,
                    limit=scroll_limit,
                    with_payload=True,
                )

            items = [_point_to_item(p) for p in points]
            items.sort(key=lambda item: item.ts_ms or 0, reverse=True)
            return items[:limit]
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
        resolved_user_id = user_id or request.headers.get("X-User-Id")
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
        resolved_user_id = user_id or request.headers.get("X-User-Id")
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
    user_id: str | None = Query(None, description="User ID (or send X-User-Id header)"),
    conversation_id: str | None = Query(None, description="Optional conversation filter"),
    query: str | None = Query(None, description="Optional semantic query"),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
):
    resolved_user_id = user_id or request.headers.get("X-User-Id")
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required (query param or X-User-Id header)",
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
