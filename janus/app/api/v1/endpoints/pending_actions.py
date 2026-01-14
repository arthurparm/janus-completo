import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel
from langgraph.types import Command
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.agents.graph_orchestrator import get_graph
# from app.db.base import get_db # Assuming we have a get_db dependency or similar for SQLAlchemy
# FIX: remove import that doesn't exist. We don't use it yet anyway.

router = APIRouter(tags=["PendingActions"], prefix="/pending_actions")
logger = logging.getLogger(__name__)

class PendingActionDTO(BaseModel):
    thread_id: str
    status: str
    message: str | None

def _resume_graph_execution(thread_id: str, resume_value: str):
    """
    Background task to resume graph execution.
    """
    logger.info(f"Resuming execution for thread {thread_id} with value {resume_value}")
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        # invoke is blocking, so running it in background task prevents API timeout
        graph.invoke(Command(resume=resume_value), config=config)
        logger.info(f"Execution finished for thread {thread_id}")
    except Exception as e:
        logger.error(f"Error in background execution for thread {thread_id}: {e}")

@router.get("/", response_model=List[PendingActionDTO])
async def list_pending():
    """
    List all threads that are currently interrupted and waiting for approval.
    Queries the checkpoints table directly using Async SQLAlchemy.
    """
    from app.db.postgres_config import postgres_db
    
    # Query to get the latest checkpoint for each thread
    # We prioritize checking metadata for 'human_approval' as it's likely JSONB and faster.
    # If not in metadata, we check the blob in Python (fallback).
    query = """
    WITH LatestCheckpoints AS (
        SELECT thread_id, checkpoint, metadata,
               ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY checkpoint_id DESC) as rn
        FROM checkpoints
    )
    SELECT thread_id, checkpoint, metadata
    FROM LatestCheckpoints
    WHERE rn = 1
    """
    
    try:
        async with postgres_db.get_session_async() as session:
            # Execute query asynchronously
            result = await session.execute(text(query))
            rows = result.fetchall()
            
            pending_actions = []
            for row in rows:
                t_id = row[0]
                ckpt = row[1]
                meta = row[2]
                
                is_approval = False
                try:
                    # 1. Check Metadata first (Fastest if JSONB/Dict)
                    if meta:
                        # If metadata is already a dict (SQLAlchemy JSON handling)
                        meta_str = json.dumps(meta) if isinstance(meta, (dict, list)) else str(meta)
                        if "human_approval" in meta_str:
                            is_approval = True
                    
                    # 2. Check Checkpoint Blob if not found in metadata
                    if not is_approval and ckpt:
                        content_str = ""
                        if isinstance(ckpt, (dict, list)):
                            content_str = json.dumps(ckpt)
                        elif isinstance(ckpt, str):
                            content_str = ckpt
                        elif isinstance(ckpt, (bytes, bytearray)):
                            # Try to decode as utf-8 (ignoring errors for binary parts)
                            # LangGraph MsgPack might have readable strings
                            content_str = ckpt.decode('utf-8', errors='ignore')
                        
                        if "human_approval" in content_str:
                            is_approval = True
                except Exception:
                    # Ignore parsing errors for individual rows
                    pass
                
                if is_approval:
                    pending_actions.append(PendingActionDTO(
                        thread_id=t_id,
                        status="pending",
                        message="Waiting for approval"
                    ))
            
            return pending_actions
            
    except Exception as e:
        logger.warning(f"Failed to query checkpoints: {e}")
        return []

@router.post("/{thread_id}/approve", response_model=PendingActionDTO, status_code=status.HTTP_202_ACCEPTED)
async def approve(thread_id: str, background_tasks: BackgroundTasks):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Check current state (fast operation)
        state = graph.get_state(config)
        if not state.next:
            raise HTTPException(status_code=404, detail="Thread not found or finished")
            
        # Update state to approved (fast operation)
        graph.update_state(config, {"approval_status": "approved"})
        
        # Schedule resume execution in background
        background_tasks.add_task(_resume_graph_execution, thread_id, "approved")
        
        return PendingActionDTO(
            thread_id=thread_id,
            status="approved",
            message="Action approved. Execution resuming in background."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{thread_id}/reject", response_model=PendingActionDTO, status_code=status.HTTP_202_ACCEPTED)
async def reject(thread_id: str, background_tasks: BackgroundTasks):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state = graph.get_state(config)
        if not state.next:
            raise HTTPException(status_code=404, detail="Thread not found")
            
        graph.update_state(config, {"approval_status": "rejected"})
        
        # Schedule resume execution in background
        background_tasks.add_task(_resume_graph_execution, thread_id, "rejected")
        
        return PendingActionDTO(
            thread_id=thread_id,
            status="rejected",
            message="Action rejected. Cleanup running in background."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting action: {e}")
        raise HTTPException(status_code=500, detail=str(e))
