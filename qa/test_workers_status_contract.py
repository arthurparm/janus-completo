import asyncio
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.workers import _task_status
from app.api.v1.endpoints.workers import router as workers_router
from app.core.workers.orchestrator import DisabledWorkerHandle
from app.main import cancel_tracked_orchestrator_workers


class _FakeTask:
    def __init__(self, done: bool, cancelled: bool, exc: Exception | None = None):
        self._done = done
        self._cancelled = cancelled
        self._exc = exc

    def done(self) -> bool:
        return self._done

    def cancelled(self) -> bool:
        return self._cancelled

    def exception(self):
        return self._exc


def test_task_status_disabled_worker():
    status = _task_status(DisabledWorkerHandle(detail="flag=false"))
    assert status["state"] == "disabled"
    assert status["reason"] == "disabled_by_config"
    assert status["running"] is False


def test_task_status_composite_worker_aggregates_children():
    running = _FakeTask(done=False, cancelled=False)
    stopped = _FakeTask(done=True, cancelled=False)
    status = _task_status((running, stopped))
    assert status["composite"] is True
    assert status["running"] is True
    assert status["state"] == "running"
    assert len(status["children"]) == 2


def test_workers_status_endpoint_exposes_disabled_and_composite():
    app = FastAPI()
    app.include_router(workers_router, prefix="/api/v1/workers")
    app.state.orchestrator_workers = [
        {
            "name": "google_productivity",
            "task": DisabledWorkerHandle(detail="ENABLE_GOOGLE_PRODUCTIVITY_WORKER=false"),
        },
        {"name": "composite_worker", "task": (_FakeTask(False, False), _FakeTask(True, False))},
    ]
    client = TestClient(app)

    resp = client.get("/api/v1/workers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracked"] == 2

    g = next(w for w in data["workers"] if w["name"] == "google_productivity")
    assert g["state"] == "disabled"
    assert g["reason"] == "disabled_by_config"

    c = next(w for w in data["workers"] if w["name"] == "composite_worker")
    assert c["composite"] is True
    assert c["state"] == "running"


def test_workers_status_endpoint_ignores_malformed_worker_items():
    app = FastAPI()
    app.include_router(workers_router, prefix="/api/v1/workers")
    app.state.orchestrator_workers = [
        {
            "name": "google_productivity",
            "task": DisabledWorkerHandle(detail="ENABLE_GOOGLE_PRODUCTIVITY_WORKER=false"),
        },
        "malformed-worker",
    ]
    client = TestClient(app)

    resp = client.get("/api/v1/workers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracked"] == 1
    assert data["ignored"] == 1
    assert data["workers"][0]["name"] == "google_productivity"
    assert data["workers"][0]["state"] == "disabled"


@pytest.mark.asyncio
async def test_shutdown_cancels_valid_workers_after_malformed_items():
    async def wait_forever():
        await asyncio.Event().wait()

    task = asyncio.create_task(wait_forever())
    composite_task = asyncio.create_task(wait_forever())
    try:
        cancelled = cancel_tracked_orchestrator_workers(
            ["malformed-worker", {"task": task}, {"task": (composite_task,)}]
        )

        assert cancelled == 2
        assert task.cancelled() or task.cancelling() > 0
        assert composite_task.cancelled() or composite_task.cancelling() > 0
    finally:
        for tracked_task in (task, composite_task):
            if not tracked_task.cancelled():
                tracked_task.cancel()
            try:
                await tracked_task
            except asyncio.CancelledError:
                pass
