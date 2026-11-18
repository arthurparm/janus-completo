import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.workers.orchestrator import (
    DisabledWorkerHandle,
    build_worker_runtime_records,
    start_all_workers,
)

router = APIRouter(tags=["Workers"])
logger = structlog.get_logger(__name__)


class WorkerTaskStatusResponse(BaseModel):
    name: str
    registered_at: datetime | None = None
    running: bool
    done: bool
    cancelled: bool
    exception: str | None = None
    state: str
    reason: str | None = None
    detail: str | None = None
    composite: bool = False
    children: list[dict[str, Any]] | None = None


class WorkersStatusResponse(BaseModel):
    tracked: int
    ignored: int
    workers: list[WorkerTaskStatusResponse]


class StartWorkersResponse(BaseModel):
    status: str
    count: int
    workers: list[WorkerTaskStatusResponse]


class StopWorkersResponse(BaseModel):
    status: str
    ignored: int
    message: str | None = None
    count: int | None = None
    stopped_count: int | None = None


def _valid_worker_records(raw_workers: Any) -> tuple[list[Mapping[str, Any]], int]:
    if not isinstance(raw_workers, list):
        logger.warning(
            "workers_invalid_collection",
            collection_type=type(raw_workers).__name__,
        )
        return [], 0 if raw_workers in (None, []) else 1

    workers: list[Mapping[str, Any]] = []
    ignored = 0
    for index, worker in enumerate(raw_workers):
        if not isinstance(worker, Mapping):
            ignored += 1
            logger.warning(
                "workers_invalid_item",
                index=index,
                item_type=type(worker).__name__,
            )
            continue
        workers.append(worker)
    return workers, ignored


def _task_status(task: Any) -> dict[str, Any]:
    if isinstance(task, DisabledWorkerHandle):
        return {
            "running": False,
            "done": False,
            "cancelled": False,
            "exception": None,
            "state": "disabled",
            "reason": task.reason,
            "detail": task.detail,
        }

    if isinstance(task, (list, tuple)):
        children = [_task_status(t) for t in task]
        first_exception = next((c.get("exception") for c in children if c.get("exception")), None)
        running = any(bool(c.get("running")) for c in children)
        done = all(bool(c.get("done")) or c.get("state") == "disabled" for c in children)
        cancelled = all(bool(c.get("cancelled")) for c in children) if children else False
        return {
            "running": running,
            "done": done,
            "cancelled": cancelled,
            "exception": first_exception,
            "state": "running" if running else ("error" if first_exception else "stopped"),
            "composite": True,
            "children": children,
        }

    try:
        if not hasattr(task, "done") or not hasattr(task, "cancelled"):
            return {
                "running": False,
                "done": False,
                "cancelled": False,
                "exception": None,
                "state": "unknown",
            }

        running = not bool(task.done()) and not bool(task.cancelled())
        done = bool(task.done())
        cancelled = bool(task.cancelled())
        exc = None
        if done and not cancelled:
            try:
                exc = task.exception()
            except Exception:
                exc = None
        return {
            "running": running,
            "done": done,
            "cancelled": cancelled,
            "exception": str(exc) if exc else None,
            "state": "running" if running else ("error" if exc else "stopped"),
        }
    except Exception:
        return {
            "running": False,
            "done": False,
            "cancelled": False,
            "exception": None,
            "state": "unknown",
        }


def _worker_status_response(worker: Mapping[str, Any]) -> WorkerTaskStatusResponse:
    return WorkerTaskStatusResponse(
        name=str(worker.get("name") or "worker"),
        registered_at=worker.get("registered_at"),
        **_task_status(worker.get("task")),
    )


def _is_worker_active(task: Any) -> bool:
    status = _task_status(task)
    return bool(status.get("running")) and status.get("state") != "disabled"


def _cancel_worker_task(task: Any) -> int:
    if isinstance(task, (list, tuple)):
        return sum(_cancel_worker_task(t) for t in task)
    if isinstance(task, asyncio.Task) and not task.cancelled():
        task.cancel()
        return 1
    return 0


@router.post(
    "/start-all",
    response_model=StartWorkersResponse,
    summary="Start all orchestrator-managed workers",
)
async def start_workers(request: Request) -> StartWorkersResponse:
    app = request.app
    # Prevent double-start if any existing worker is still running
    current, _ignored = _valid_worker_records(getattr(app.state, "orchestrator_workers", []) or [])
    if any(_is_worker_active(w.get("task")) for w in current):
        raise HTTPException(status_code=400, detail="Workers already running. Stop them first.")

    workers = await start_all_workers()
    payload = build_worker_runtime_records(workers)
    app.state.orchestrator_workers = payload

    return StartWorkersResponse(
        status="started",
        workers=[_worker_status_response(w) for w in payload],
        count=len(payload),
    )


@router.post(
    "/stop-all",
    response_model=StopWorkersResponse,
    summary="Stop all orchestrator-managed workers",
)
async def stop_workers(request: Request) -> StopWorkersResponse:
    app = request.app
    current, ignored = _valid_worker_records(getattr(app.state, "orchestrator_workers", []) or [])
    if not current:
        app.state.orchestrator_workers = []
        return StopWorkersResponse(
            status="ok",
            message="No workers tracked",
            count=0,
            ignored=ignored,
        )

    stopped = 0
    for w in current:
        t = w.get("task")
        stopped += _cancel_worker_task(t)
    # Clear state registry
    app.state.orchestrator_workers = []

    return StopWorkersResponse(status="stopped", stopped_count=stopped, ignored=ignored)


@router.get(
    "/status",
    response_model=WorkersStatusResponse,
    summary="Get status for orchestrator-managed workers",
)
async def workers_status(request: Request) -> WorkersStatusResponse:
    app = request.app
    current, ignored = _valid_worker_records(getattr(app.state, "orchestrator_workers", []) or [])
    return WorkersStatusResponse(
        tracked=len(current),
        ignored=ignored,
        workers=[_worker_status_response(w) for w in current],
    )
