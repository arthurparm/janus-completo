import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from app.core.workers.orchestrator import start_all_workers

router = APIRouter(tags=["Workers"])


def _task_status(task: asyncio.Task) -> Dict[str, Any]:
    try:
        running = not task.done() and not task.cancelled()
        done = task.done()
        cancelled = task.cancelled()
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
        }
    except Exception:
        return {"running": False, "done": False, "cancelled": False, "exception": None}


@router.post("/start-all", summary="Start all orchestrator-managed workers")
async def start_workers(request: Request):
    app = request.app
    # Prevent double-start if any existing worker is still running
    current: List[Dict[str, Any]] = getattr(app.state, "orchestrator_workers", []) or []
    if any((isinstance(w.get("task"), asyncio.Task) and not w["task"].done() and not w["task"].cancelled()) for w in current):
        raise HTTPException(status_code=400, detail="Workers already running. Stop them first.")

    workers = await start_all_workers()
    names = [
        "knowledge_consolidation",
        "agent_tasks",
        "neural_training",
        "meta_agent",
        "auto_scaler",
        "auto_healer",
        "router",
        "code_agent",
        "professor_agent",
        "sandbox_agent",
        "autonomy",
        "google_productivity",
    ]
    payload = []
    for idx, task in enumerate(workers):
        name = names[idx] if idx < len(names) else f"worker_{idx}"
        payload.append({"name": name, "task": task})
    app.state.orchestrator_workers = payload

    return {
        "status": "started",
        "workers": [{"name": w["name"], **_task_status(w["task"])} for w in payload],
        "count": len(payload),
    }


@router.post("/stop-all", summary="Stop all orchestrator-managed workers")
async def stop_workers(request: Request):
    app = request.app
    current: List[Dict[str, Any]] = getattr(app.state, "orchestrator_workers", []) or []
    if not current:
        return {"status": "ok", "message": "No workers tracked", "count": 0}

    stopped = 0
    for w in current:
        t = w.get("task")
        if isinstance(t, asyncio.Task) and not t.cancelled():
            t.cancel()
            stopped += 1
    # Clear state registry
    app.state.orchestrator_workers = []

    return {"status": "stopped", "stopped_count": stopped}


@router.get("/status", summary="Get status for orchestrator-managed workers")
async def workers_status(request: Request):
    app = request.app
    current: List[Dict[str, Any]] = getattr(app.state, "orchestrator_workers", []) or []
    return {
        "tracked": len(current),
        "workers": [{"name": w["name"], **_task_status(w["task"])} for w in current],
    }