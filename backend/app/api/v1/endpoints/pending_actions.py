import asyncio
import json
from typing import Any, List

import structlog
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from langgraph.types import Command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from app.core.agents.graph_orchestrator import get_graph
from app.core.security.redaction import redact_sensitive_payload

router = APIRouter(tags=["PendingActions"], prefix="/pending_actions")
logger = structlog.get_logger(__name__)

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
    risk_level: str | None = None
    risk_summary: str | None = None
    scope_summary: str | None = None
    scope_targets: list[str] | None = None
    simulation: dict[str, Any] | None = None


_HIGH_RISK_KEYWORDS = (
    "delete",
    "drop",
    "truncate",
    "remove",
    "rm ",
    "shutdown",
    "reboot",
    "kill",
    "reset",
    "wipe",
    "format",
    "powershell",
    "bash",
    "cmd ",
)
_MEDIUM_RISK_KEYWORDS = (
    "write",
    "create",
    "update",
    "patch",
    "edit",
    "modify",
    "insert",
    "exec",
    "run",
    "deploy",
)
_LOW_RISK_TOOL_PREFIXES = (
    "list_",
    "read_",
    "get_",
    "query_",
    "recall_",
    "search_",
)


def _summarize_action_risk(tool_name: str | None, args_json: str | None) -> tuple[str, str]:
    tool = str(tool_name or "").strip()
    args_text = str(args_json or "")
    text = f"{tool} {args_text}".lower()

    if any(keyword in text for keyword in _HIGH_RISK_KEYWORDS):
        return ("high", "Alto risco: pode alterar ou remover dados/sistema.")
    if any(keyword in text for keyword in _MEDIUM_RISK_KEYWORDS):
        return ("medium", "Risco moderado: pode modificar estado do sistema.")

    if tool and any(tool.lower().startswith(prefix) for prefix in _LOW_RISK_TOOL_PREFIXES):
        return ("low", "Baixo risco: ferramenta de leitura/consulta.")

    if args_json:
        try:
            parsed = json.loads(args_json)
            if isinstance(parsed, dict) and parsed:
                return ("medium", "Acao com parametros: revise os argumentos antes de aprovar.")
        except Exception:
            pass

    return ("low", "Baixo risco: leitura/consulta sem alteracao relevante esperada.")


def _sanitize_pending_args_json(args_json: str | None) -> str | None:
    if args_json is None:
        return None
    raw_text = str(args_json)
    if not raw_text.strip():
        return raw_text

    try:
        parsed = json.loads(raw_text)
        return json.dumps(redact_sensitive_payload(parsed), ensure_ascii=False)
    except Exception:
        return str(redact_sensitive_payload(raw_text))


def _extract_pending_scope(args_json: str | None) -> tuple[str | None, list[str] | None]:
    if not args_json:
        return None, None
    try:
        parsed = json.loads(args_json)
    except Exception:
        return None, None
    if not isinstance(parsed, dict):
        return None, None
    scope_summary = parsed.get("scope_summary")
    scope_targets = parsed.get("scope_targets")
    if isinstance(scope_targets, list):
        safe_targets = [str(item) for item in scope_targets if str(item).strip()]
    else:
        safe_targets = []
    return (
        str(scope_summary).strip() if isinstance(scope_summary, str) and scope_summary.strip() else None,
        safe_targets or None,
    )


def _build_simulation_payload(item: Any) -> dict[str, Any] | None:
    raw = getattr(item, "simulation_summary_json", None)
    generated_at = getattr(item, "simulation_generated_at", None)
    version = getattr(item, "simulation_version", None)
    if raw is None and generated_at is None and version is None:
        return None

    parsed: dict[str, Any]
    if isinstance(raw, str) and raw.strip():
        try:
            candidate = json.loads(raw)
            parsed = candidate if isinstance(candidate, dict) else {"summary": str(candidate)}
        except Exception:
            parsed = {"summary": str(raw)}
    else:
        parsed = {}

    safe = redact_sensitive_payload(parsed)
    if generated_at is not None:
        try:
            safe["generated_at"] = generated_at.isoformat()
        except Exception:
            safe["generated_at"] = str(generated_at)
    if version:
        safe["simulation_version"] = str(version)
    return safe or None


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


def _load_pending_action_context(args_json: str | None) -> dict[str, Any]:
    if not args_json:
        return {}
    try:
        parsed = json.loads(args_json)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_resolved_confirmation_payload(
    confirmation: dict[str, Any] | None,
    *,
    status_value: str,
) -> dict[str, Any]:
    payload = dict(confirmation or {})
    payload["required"] = False
    payload["status"] = status_value
    payload.pop("approve_endpoint", None)
    payload.pop("reject_endpoint", None)
    return payload


def _build_resolved_understanding_payload(
    understanding: dict[str, Any] | None,
    *,
    status_value: str,
) -> dict[str, Any] | None:
    if not isinstance(understanding, dict):
        return understanding
    payload = dict(understanding)
    payload["requires_confirmation"] = False
    nested_confirmation = payload.get("confirmation")
    if isinstance(nested_confirmation, dict):
        payload["confirmation"] = _build_resolved_confirmation_payload(
            nested_confirmation,
            status_value=status_value,
        )
    return payload


def _build_resolved_agent_state_payload(
    agent_state: dict[str, Any] | None,
    *,
    status_value: str,
) -> dict[str, Any]:
    payload = dict(agent_state or {})
    payload["state"] = "completed"
    payload["requires_confirmation"] = False
    payload["reason"] = status_value
    return payload


def _build_resolved_chat_message_patch(
    message: dict[str, Any],
    *,
    status_value: str,
) -> dict[str, Any]:
    confirmation = (
        message.get("confirmation") if isinstance(message.get("confirmation"), dict) else None
    )
    understanding = (
        message.get("understanding") if isinstance(message.get("understanding"), dict) else None
    )
    agent_state = (
        message.get("agent_state") if isinstance(message.get("agent_state"), dict) else None
    )
    return {
        "confirmation": _build_resolved_confirmation_payload(
            confirmation,
            status_value=status_value,
        ),
        "understanding": _build_resolved_understanding_payload(
            understanding,
            status_value=status_value,
        ),
        "agent_state": _build_resolved_agent_state_payload(
            agent_state,
            status_value=status_value,
        ),
    }


def _sync_chat_confirmation_for_action(action: Any, *, status_value: str) -> None:
    context = _load_pending_action_context(getattr(action, "args_json", None))
    conversation_id = context.get("conversation_id")
    if conversation_id is None:
        return

    from app.repositories.chat_repository_sql import ChatRepositorySQL

    repo = ChatRepositorySQL()
    try:
        messages = repo.get_history(str(conversation_id))
    except Exception as e:
        logger.warning(
            "pending_action_chat_sync_history_failed",
            action_id=getattr(action, "id", None),
            conversation_id=conversation_id,
            error=str(e),
        )
        return

    action_id = getattr(action, "id", None)
    matched = 0
    for message in messages:
        confirmation = message.get("confirmation")
        if str(message.get("role")) != "assistant" or not isinstance(confirmation, dict):
            continue
        if confirmation.get("pending_action_id") != action_id:
            continue
        message_id = message.get("id")
        if message_id is None:
            continue
        patch = _build_resolved_chat_message_patch(message, status_value=status_value)
        try:
            repo.update_message_payload(
                str(conversation_id),
                int(message_id),
                patch,
            )
            matched += 1
        except Exception as e:
            logger.warning(
                "pending_action_chat_sync_update_failed",
                action_id=action_id,
                conversation_id=conversation_id,
                message_id=message_id,
                error=str(e),
            )

    if matched == 0:
        logger.info(
            "pending_action_chat_sync_no_matching_message",
            action_id=action_id,
            conversation_id=conversation_id,
        )


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
        logger.warning("log_warning", message=f"Failed to verify thread existence in checkpoints: {e}")
        if _is_backend_unavailable_error(e):
            raise
        return None


async def _resume_graph_execution(thread_id: str, resume_value: str):
    """
    Background task to resume graph execution.
    """
    logger.info("log_info", message=f"Resuming execution for thread {thread_id} with value {resume_value}")
    try:
        graph = get_graph()
        await _invoke_resume(graph, thread_id, resume_value)
        logger.info("log_info", message=f"Execution finished for thread {thread_id}")
    except Exception as e:
        logger.error("log_error", message=f"Error in background execution for thread {thread_id}: {e}", exc_info=True)

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
                safe_args_json = _sanitize_pending_args_json(getattr(item, "args_json", None))
                scope_summary, scope_targets = _extract_pending_scope(safe_args_json)
                risk_level, risk_summary = _summarize_action_risk(
                    getattr(item, "tool_name", None), safe_args_json
                )
                items.append(
                    PendingActionDTO(
                        source="sql",
                        action_id=getattr(item, "id", None),
                        status=getattr(item, "status", "pending"),
                        message=f"Waiting approval for tool: {getattr(item, 'tool_name', '-')}",
                        user_id=getattr(item, "user_id", None),
                        tool_name=getattr(item, "tool_name", None),
                        args_json=safe_args_json,
                        created_at=(
                            getattr(item, "created_at", None).isoformat()
                            if getattr(item, "created_at", None)
                            else None
                        ),
                        risk_level=risk_level,
                        risk_summary=risk_summary,
                        scope_summary=scope_summary,
                        scope_targets=scope_targets,
                        simulation=_build_simulation_payload(item),
                    )
                )
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to query SQL pending actions: {e}")
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
                    logger.warning("log_warning", message=f"Failed to inspect graph state for thread {tid}: {e}")
                    return tid, False

            checks = await asyncio.gather(*(_is_waiting_for_approval(tid) for tid in thread_ids))
            graph_items = [
                PendingActionDTO(
                    source="langgraph",
                    thread_id=tid,
                    status="pending",
                    message="Waiting for approval",
                    risk_level="medium",
                    risk_summary="Risco moderado: acao aguardando aprovacao humana.",
                )
                for tid, waiting in checks
                if waiting
            ]
            return items + graph_items
    except Exception as e:
        logger.warning("log_warning", message=f"Failed to query checkpoints: {e}")
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
            message="Action approved. Execution resuming in background.",
            risk_level="medium",
            risk_summary="Acao aprovada e retomada em background.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("log_error", message=f"Error approving action: {e}")
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
        _sync_chat_confirmation_for_action(updated, status_value="approved")

        safe_args_json = _sanitize_pending_args_json(getattr(updated, "args_json", None))
        scope_summary, scope_targets = _extract_pending_scope(safe_args_json)
        risk_level, risk_summary = _summarize_action_risk(
            getattr(updated, "tool_name", None), safe_args_json
        )
        return PendingActionDTO(
            source="sql",
            action_id=getattr(updated, "id", None),
            status=getattr(updated, "status", "approved"),
            message="Action approved.",
            user_id=getattr(updated, "user_id", None),
            tool_name=getattr(updated, "tool_name", None),
            args_json=safe_args_json,
            created_at=(
                getattr(updated, "created_at", None).isoformat()
                if getattr(updated, "created_at", None)
                else None
            ),
            risk_level=risk_level,
            risk_summary=risk_summary,
            scope_summary=scope_summary,
            scope_targets=scope_targets,
            simulation=_build_simulation_payload(updated),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("log_error", message=f"Error approving SQL pending action: {e}")
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
        _sync_chat_confirmation_for_action(updated, status_value="rejected")

        safe_args_json = _sanitize_pending_args_json(getattr(updated, "args_json", None))
        scope_summary, scope_targets = _extract_pending_scope(safe_args_json)
        risk_level, risk_summary = _summarize_action_risk(
            getattr(updated, "tool_name", None), safe_args_json
        )
        return PendingActionDTO(
            source="sql",
            action_id=getattr(updated, "id", None),
            status=getattr(updated, "status", "rejected"),
            message="Action rejected.",
            user_id=getattr(updated, "user_id", None),
            tool_name=getattr(updated, "tool_name", None),
            args_json=safe_args_json,
            created_at=(
                getattr(updated, "created_at", None).isoformat()
                if getattr(updated, "created_at", None)
                else None
            ),
            risk_level=risk_level,
            risk_summary=risk_summary,
            scope_summary=scope_summary,
            scope_targets=scope_targets,
            simulation=_build_simulation_payload(updated),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("log_error", message=f"Error rejecting SQL pending action: {e}")
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
            message="Action rejected. Cleanup running in background.",
            risk_level="medium",
            risk_summary="Acao rejeitada e cleanup em background.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("log_error", message=f"Error rejecting action: {e}")
        if _is_backend_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Pending action backend is unavailable (checkpoint storage inaccessible).",
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error")
