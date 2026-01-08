import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.schemas import ScoredExperience
from app.services.memory_service import MemoryService, get_memory_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/timeline", response_model=List[ScoredExperience])
async def get_memories_timeline(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601), inclusive"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601), inclusive"),
    query: Optional[str] = Query(None, description="Semantic text query to filter memories"),
    limit: int = Query(10, ge=1, le=100),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    service: MemoryService = Depends(get_memory_service)
):
    """
    Retrieves memories within a specific timeframe ("Time Travel").
    Allows semantic filtering via `query`.
    """
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None

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
            detail=f"Invalid date format. Use ISO 8601 (e.g., 2023-01-01T12:00:00Z). Error: {e}"
        )

    try:
        memories = await service.recall_by_timeframe(
            query=query,
            start_ts_ms=start_ts,
            end_ts_ms=end_ts,
            limit=limit,
            min_score=min_score
        )
        return memories
    except Exception as e:
        logger.error(f"Error retrieving timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve timeline memories"
        )
