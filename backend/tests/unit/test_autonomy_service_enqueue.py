import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.autonomy import router as autonomy_router
from app.core.autonomy.goal_manager import Goal, GoalStatus
from app.services.autonomy_service import AutonomyService, get_autonomy_service


class _FakeOptimizationService:
    async def get_system_health(self) -> dict:
        return {
            "health_score": 1.0,
            "avg_response_time": 0.0,
            "error_rate": 0.0,
            "tool_success_rate": 1.0,
            "active_tools_count": 1,
            "failed_tools": [],
            "slow_tools": [],
        }


class _FakeRepo:
    def __init__(self):
        self.steps: list[dict] = []
        self._ledger_by_key: dict[str, SimpleNamespace] = {}
        self._next_ledger_id = 1

    def add_step(self, **kwargs):
        self.steps.append(kwargs)
        return SimpleNamespace(id=1)

    def create_or_get_enqueue_ledger(
        self,
        *,
        run_id: int | None,
        goal_id: str,
        cycle: int,
        selected_tool: str | None,
        idempotency_key: str,
    ):
        if idempotency_key in self._ledger_by_key:
            return self._ledger_by_key[idempotency_key]
        row = SimpleNamespace(
            id=self._next_ledger_id,
            run_id=run_id,
            goal_id=goal_id,
            cycle=cycle,
            selected_tool=selected_tool,
            idempotency_key=idempotency_key,
            publish_status="pending",
            task_id=None,
            publish_error=None,
        )
        self._next_ledger_id += 1
        self._ledger_by_key[idempotency_key] = row
        return row

    def mark_enqueue_published(self, ledger_id: int, task_id: str):
        for row in self._ledger_by_key.values():
            if row.id == ledger_id:
                row.publish_status = "published"
                row.task_id = task_id
                row.publish_error = None
                return row
        return None

    def mark_enqueue_failed(self, ledger_id: int, error: str):
        for row in self._ledger_by_key.values():
            if row.id == ledger_id:
                row.publish_status = "failed"
                row.publish_error = error
                return row
        return None


class _FakeGoalManager:
    def __init__(self, goal: Goal | None):
        self._goal = goal
        self.status_updates: list[tuple[str, str]] = []

    def get_next_goal(self):
        return self._goal

    def update_goal_status(self, goal_id: str, status: str, **_kwargs):
        self.status_updates.append((goal_id, status))
        if self._goal and self._goal.id == goal_id:
            self._goal.status = status
        return self._goal


@pytest.mark.asyncio
async def test_autonomy_service_enqueue_router_records_synthetic_step():
    goal = Goal(id="g1", title="Pesquisar docs", description="Buscar contexto")
    goal_manager = _FakeGoalManager(goal)
    repo = _FakeRepo()
    collab = SimpleNamespace(pass_task=AsyncMock(return_value="task-1"))

    service = AutonomyService(
        optimization_service=_FakeOptimizationService(),
        llm_service=None,
        goal_manager=goal_manager,
        repo=repo,
        collaboration_service=collab,
    )
    service._current_run_id = 42

    await service._run_cycle_enqueue()

    assert goal_manager.status_updates[0] == ("g1", GoalStatus.IN_PROGRESS)
    collab.pass_task.assert_awaited_once()
    assert repo.steps, "expected synthetic history step for enqueue mode"
    assert repo.steps[-1]["tool"] == "autonomy_enqueue"
    assert repo.steps[-1]["success"] is True
    assert "task_id=" in repo.steps[-1]["result_preview"]


@pytest.mark.asyncio
async def test_autonomy_service_enqueue_router_reverts_goal_to_pending_on_publish_error():
    goal = Goal(id="g2", title="Falhar enqueue", description="Teste")
    goal_manager = _FakeGoalManager(goal)
    repo = _FakeRepo()
    collab = SimpleNamespace(pass_task=AsyncMock(side_effect=RuntimeError("broker down")))

    service = AutonomyService(
        optimization_service=_FakeOptimizationService(),
        llm_service=None,
        goal_manager=goal_manager,
        repo=repo,
        collaboration_service=collab,
    )
    service._current_run_id = 43

    with pytest.raises(RuntimeError, match="broker down"):
        await service._run_cycle_enqueue()

    assert ("g2", GoalStatus.IN_PROGRESS) in goal_manager.status_updates
    assert ("g2", GoalStatus.PENDING) in goal_manager.status_updates
    assert repo.steps[-1]["tool"] == "autonomy_enqueue"
    assert repo.steps[-1]["success"] is False


def test_autonomy_status_includes_execution_mode():
    service = AutonomyService(optimization_service=_FakeOptimizationService())
    status = service.get_status()
    assert status["config"]["execution_mode"] == "enqueue_router"
    assert "runtime_lock" in status


@pytest.mark.asyncio
async def test_autonomy_service_enqueue_router_skips_duplicate_published_ledger():
    goal = Goal(id="g3", title="Meta duplicada", description="Teste idempotencia")
    goal_manager = _FakeGoalManager(goal)
    repo = _FakeRepo()
    collab = SimpleNamespace(pass_task=AsyncMock(return_value="task-dup"))

    # Pre-seed the deterministic ledger key for cycle 1 of run 44
    key = "goal:g3:run:44:cycle:1"
    repo._ledger_by_key[key] = SimpleNamespace(
        id=99,
        run_id=44,
        goal_id="g3",
        cycle=1,
        selected_tool="get_system_info",
        idempotency_key=key,
        publish_status="published",
        task_id="task-existing",
        publish_error=None,
    )

    service = AutonomyService(
        optimization_service=_FakeOptimizationService(),
        llm_service=None,
        goal_manager=goal_manager,
        repo=repo,
        collaboration_service=collab,
    )
    service._current_run_id = 44

    await service._run_cycle_enqueue()

    collab.pass_task.assert_not_awaited()
    assert repo.steps[-1]["success"] is True
    assert "idempotent_skip" in repo.steps[-1]["result_preview"]


class _DummyAutonomyService:
    async def start(self, _config):
        return True

    async def stop(self):
        return True

    def get_status(self):
        return {
            "active": False,
            "cycle_count": 0,
            "last_cycle_at": None,
            "config": {"execution_mode": "enqueue_router"},
        }

    def update_plan(self, _plan):
        return None

    def update_policy_config(self, **_kwargs):
        return None


def test_autonomy_start_rejects_invalid_execution_mode():
    app = FastAPI()
    app.include_router(autonomy_router, prefix="/api/v1/autonomy")
    app.dependency_overrides[get_autonomy_service] = lambda: _DummyAutonomyService()
    client = TestClient(app)

    resp = client.post("/api/v1/autonomy/start", json={"execution_mode": "direct_execute"})
    assert resp.status_code == 422
