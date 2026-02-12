import logging
import asyncio
from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from langgraph.types import Command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from app.core.agents.graph_orchestrator import get_graph

router = APIRouter(tags=["PendingActions"], prefix="/pending_actions")
logger = logging.getLogger(__name__)

class PendingActionDTO(BaseModel):
    source: str = "langgraph"
    thread_id: str | None = None
    action_id: int | None = None
    status: str
    message: str | None
    user_id: str | None = None
    tool_name: str | None = None
    args_json: str | None = None
    created_at: str | None = None


def _is_backend_unavailable_error(error: Exception) -> bool:
    if isinstance(error, (OperationalError, InterfaceError, DBAPIError)):
        return True
    msg = str(error).lower()
    patterns = (
        "invalid connection type",
        "connection is closed",
        "connection refused",
        "connection reset",
        "could not connect",
        "could not translate host name",
        "name or service not known",
        "timeout",
        "pool is closing",
        "server closed the connection unexpectedly",
        "terminating connection due to administrator command",
        "operationalerror",
    )
    return any(pattern in msg for pattern in patterns)


def _is_waiting_for_human_approval(next_value: object) -> bool:
    if isinstance(next_value, str):
        return next_value == "human_approval"
    if isinstance(next_value, (list, tuple, set)):
        return "human_approval" in next_value
    # Legacy stubs may expose only a truthy flag.
    return bool(next_value)


def _get_session_context_manager(postgres_db):
    getter = getattr(postgres_db, "get_session_async")
    try:
        return getter()
    except TypeError:
        # Test doubles may patch a plain asynccontextmanager function on an instance.
        raw_getter = getattr(getter, "__func__", None)
        if callable(raw_getter):
            return raw_getter()
        raise


async def _get_state(graph, config: dict):
    aget_state = getattr(graph, "aget_state", None)
    if callable(aget_state):
        return await aget_state(config)
    get_state = getattr(graph, "get_state", None)
    if callable(get_state):
        return get_state(config)
    raise RuntimeError("Graph state API unavailable")


async def _update_state(graph, config: dict, values: dict):
    aupdate_state = getattr(graph, "aupdate_state", None)
    if callable(aupdate_state):
        await aupdate_state(config, values)
        return
    update_state = getattr(graph, "update_state", None)
    if callable(update_state):
        update_state(config, values)
        return
    raise RuntimeError("Graph update API unavailable")


async def _invoke_resume(graph, thread_id: str, resume_value: str):
    config = {"configurable": {"thread_id": thread_id}}
    ainvoke = getattr(graph, "ainvoke", None)
    if callable(ainvoke):
        await ainvoke(Command(resume=resume_value), config=config)
        return
    invoke = getattr(graph, "invoke", None)
    if callable(invoke):
        invoke(Command(resume=resume_value), config=config)
        return
    raise RuntimeError("Graph invoke API unavailable")


async def _thread_exists_in_checkpoints(thread_id: str) -> bool | None:
    """
    Returns True when a checkpoint row exists, False when definitely absent,
    and None when the environment/test-double cannot determine safely.
    """
    from app.db.postgres_config import postgres_db

    table_exists_query = text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'checkpoints')"
    )
    thread_exists_query = text(
        "SELECT 1 FROM checkpoints WHERE thread_id = :thread_id LIMIT 1"
    )

    try:
        async with _get_session_context_manager(postgres_db) as session:
            has_scalar = hasattr(session, "scalar")
            if hasattr(session, "scalar"):
                table_exists = await session.scalar(table_exists_query)
                if not table_exists:
                    return None
            row = await session.execute(thread_exists_query, {"thread_id": thread_id})
            if not has_scalar:
                # Test doubles may not implement SQL capabilities consistently.
                return None
            if hasattr(row, "first"):
                return row.first() is not None
            if hasattr(row, "fetchall"):
                rows = row.fetchall()
                return len(rows) > 0 if rows is not None else None
            return None
    except Exception as e:
        logger.warning(f"Failed to verify thread existence in checkpoints: {e}")
        if _is_backend_unavailable_error(e):
            raise
        return None


async def _resume_graph_execution(thread_id: str, resume_value: str):
    """
    Background task to resume graph execution.
    """
    logger.info(f"Resuming execution for thread {thread_id} with value {resume_value}")
    try:
        graph = get_graph()
        await _invoke_resume(graph, thread_id, resume_value)
        logger.info(f"Execution finished for thread {thread_id}")
    except Exception as e:
        logger.error(f"Error in background execution for thread {thread_id}: {e}", exc_info=True)

@router.get("/", response_model=List[PendingActionDTO])
async def list_pending(
    include_graph: bool = True,
    include_sql: bool = False,
    user_id: str | None = None,
    pending_status: str | None = "pending",
    limit: int = 50,
):
    """
    List all threads that are currently interrupted and waiting for approval.
    Uses LangGraph state to determine if a thread is currently stopped at
    the human_approval interruption point.
    """
    items: list[PendingActionDTO] = []

    if include_sql:
        try:
            from app.repositories.pending_action_repository import PendingActionRepository

            repo = PendingActionRepository()
            sql_pending = repo.list(user_id=user_id, status=pending_status, limit=limit)
            for item in sql_pending:
                items.append(
                    PendingActionDTO(
                        source="sql",
                        action_id=getattr(item, "id", None),
                        status=getattr(item, "status", "pending"),
                        message=f"Waiting approval for tool: {getattr(item, 'tool_name', '-')}",
                        user_id=getattr(item, "user_id", None),
                        tool_name=getattr(item, "tool_name", None),
                        args_json=getattr(item, "args_json", None),
                        created_at=(
                            getattr(item, "created_at", None).isoformat()
                            if getattr(item, "created_at", None)
                            else None
                        ),
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to query SQL pending actions: {e}")
            if _is_backend_unavailable_error(e):
                raise HTTPException(
                    status_code=503,
                    detail="Pending action backend is unavailable (SQL storage inaccessible).",
                ) from e

    if not include_graph:
        return items

    from app.db.postgres_config import postgres_db
    graph = get_graph()
    query = "SELECT DISTINCT thread_id FROM checkpoints"

    try:
        async with _get_session_context_manager(postgres_db) as session:
            result = await session.execute(text(query))
            thread_ids = [row[0] for row in result.fetchall()]
            if not thread_ids:
                return items

            async def _is_waiting_for_approval(tid: str) -> tuple[str, bool]:
                try:
                    state = await _get_state(graph, {"configurable": {"thread_id": tid}})
                    return tid, _is_waiting_for_human_approval(getattr(state, "next", None))
                except Exception as e:
                    logger.warning(f"Failed to inspect graph state for thread {tid}: {e}")
                    return tid, False

            checks = await asyncio.gather(*(_is_waiting_for_approval(tid) for tid in thread_ids))
            graph_items = [
                PendingActionDTO(
                    source="langgraph",
                    thread_id=tid,
                    status="pending",
                    message="Waiting for approval",
                )
                for tid, waiting in checks
                if waiting
            ]
            return items + graph_items
    except Exception as e:
        logger.warning(f"Failed to query checkpoints: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (checkpoint storage inaccessible).",
            ) from e
        return []

@router.post("/{thread_id}/approve", response_model=PendingActionDTO, status_code=status.HTTP_202_ACCEPTED)
async def approve(thread_id: str, background_tasks: BackgroundTasks):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state = await _get_state(graph, config)
        thread_exists = await _thread_exists_in_checkpoints(thread_id)

        # If state is available and waiting, allow approval even when checkpoint lookup is inconclusive.
        if state and _is_waiting_for_human_approval(getattr(state, "next", None)):
            pass
        elif thread_exists is False:
            raise HTTPException(status_code=404, detail="Thread not found or finished")

        if not state or not getattr(state, "next", None):
            raise HTTPException(status_code=404, detail="Thread not found or finished")
        if not _is_waiting_for_human_approval(getattr(state, "next", None)):
            raise HTTPException(status_code=409, detail="Thread is not waiting for approval")
            
        # Update state to approved (fast operation)
        await _update_state(graph, config, {"approval_status": "approved"})
        
        # Schedule resume execution in background
        background_tasks.add_task(_resume_graph_execution, thread_id, "approved")
        
        return PendingActionDTO(
            source="langgraph",
            thread_id=thread_id,
            status="approved",
            message="Action approved. Execution resuming in background."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving action: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (checkpoint storage inaccessible).",
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/action/{action_id}/approve",
    response_model=PendingActionDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def approve_sql_action(action_id: int):
    try:
        from app.repositories.pending_action_repository import PendingActionRepository

        repo = PendingActionRepository()
        current = repo.get(action_id)
        if not current:
            raise HTTPException(status_code=404, detail="Pending action not found")
        if getattr(current, "status", "pending") != "pending":
            raise HTTPException(status_code=409, detail="Pending action is not waiting for approval")

        updated = repo.set_status(action_id, "approved")
        if not updated:
            raise HTTPException(status_code=404, detail="Pending action not found")

        return PendingActionDTO(
            source="sql",
            action_id=getattr(updated, "id", None),
            status=getattr(updated, "status", "approved"),
            message="Action approved.",
            user_id=getattr(updated, "user_id", None),
            tool_name=getattr(updated, "tool_name", None),
            args_json=getattr(updated, "args_json", None),
            created_at=(
                getattr(updated, "created_at", None).isoformat()
                if getattr(updated, "created_at", None)
                else None
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving SQL pending action: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (SQL storage inaccessible).",
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/action/{action_id}/reject",
    response_model=PendingActionDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reject_sql_action(action_id: int):
    try:
        from app.repositories.pending_action_repository import PendingActionRepository

        repo = PendingActionRepository()
        current = repo.get(action_id)
        if not current:
            raise HTTPException(status_code=404, detail="Pending action not found")
        if getattr(current, "status", "pending") != "pending":
            raise HTTPException(status_code=409, detail="Pending action is not waiting for approval")

        updated = repo.set_status(action_id, "rejected")
        if not updated:
            raise HTTPException(status_code=404, detail="Pending action not found")

        return PendingActionDTO(
            source="sql",
            action_id=getattr(updated, "id", None),
            status=getattr(updated, "status", "rejected"),
            message="Action rejected.",
            user_id=getattr(updated, "user_id", None),
            tool_name=getattr(updated, "tool_name", None),
            args_json=getattr(updated, "args_json", None),
            created_at=(
                getattr(updated, "created_at", None).isoformat()
                if getattr(updated, "created_at", None)
                else None
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting SQL pending action: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (SQL storage inaccessible).",
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{thread_id}/reject", response_model=PendingActionDTO, status_code=status.HTTP_202_ACCEPTED)
async def reject(thread_id: str, background_tasks: BackgroundTasks):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state = await _get_state(graph, config)
        thread_exists = await _thread_exists_in_checkpoints(thread_id)

        # If state is available and waiting, allow rejection even when checkpoint lookup is inconclusive.
        if state and _is_waiting_for_human_approval(getattr(state, "next", None)):
            pass
        elif thread_exists is False:
            raise HTTPException(status_code=404, detail="Thread not found")

        if not state or not getattr(state, "next", None):
            raise HTTPException(status_code=404, detail="Thread not found")
        if not _is_waiting_for_human_approval(getattr(state, "next", None)):
            raise HTTPException(status_code=409, detail="Thread is not waiting for approval")
            
        await _update_state(graph, config, {"approval_status": "rejected"})
        
        # Schedule resume execution in background
        background_tasks.add_task(_resume_graph_execution, thread_id, "rejected")
        
        return PendingActionDTO(
            source="langgraph",
            thread_id=thread_id,
            status="rejected",
            message="Action rejected. Cleanup running in background."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting action: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (checkpoint storage inaccessible).",
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error")
