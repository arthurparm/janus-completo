import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.memory.generative_memory import generative_memory_service
from app.models.schemas import Experience, ScoredExperience
from app.services.memory_service import MemoryService, get_memory_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/timeline", response_model=list[ScoredExperience])
async def get_memories_timeline(
    start_date: str | None = Query(None, description="Start date (ISO 8601), inclusive"),
    end_date: str | None = Query(None, description="End date (ISO 8601), inclusive"),
    query: str | None = Query(None, description="Semantic text query to filter memories"),
    limit: int = Query(10, ge=1, le=100),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
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

    try:
        memories = await service.recall_by_timeframe(
            query=query, start_ts_ms=start_ts, end_ts_ms=end_ts, limit=limit, min_score=min_score
        )
        return memories
    except Exception as e:
        logger.error(f"Error retrieving timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve timeline memories",
        )


@router.get("/generative", response_model=list[ScoredExperience])
async def get_generative_memories(
    query: str = Query(..., description="Query for memory retrieval"),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Retrieves memories using the Generative Agents scoring (Recency * Importance * Relevance).
    """
    try:
        memories = await generative_memory_service.retrieve_memories(query, limit=limit)
        return memories
    except Exception as e:
        logger.error(f"Error retrieving generative memories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve generative memories: {e}",
        )


@router.post("/generative", response_model=Experience)
async def add_generative_memory(
    content: str,
    importance: float | None = Query(None, ge=0.0, le=10.0),
    type: str = "episodic",
):
    """
    Adds a memory to the Generative Stream (calculates importance if missing).
    """
    try:
        meta = {}
        if importance is not None:
            meta["importance"] = importance

        memory = await generative_memory_service.add_memory(content, type=type, metadata=meta)
        return memory
    except Exception as e:
        logger.error(f"Error adding generative memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add generative memory: {e}",
        )
