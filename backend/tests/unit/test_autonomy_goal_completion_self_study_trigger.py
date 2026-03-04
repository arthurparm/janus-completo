from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.v1.endpoints.autonomy as autonomy_module
from app.api.v1.endpoints.autonomy import router as autonomy_router
from app.core.autonomy.goal_manager import get_goal_manager


class _GoalManagerStub:
    def update_goal_status(self, goal_id: str, status: str):
        return SimpleNamespace(
            id=goal_id,
            title="goal",
            description="desc",
            priority=5,
            status=status,
            success_criteria=None,
            deadline_ts=None,
            created_at=1.0,
            updated_at=2.0,
        )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(autonomy_router, prefix="/api/v1/autonomy")
    app.dependency_overrides[get_goal_manager] = lambda: _GoalManagerStub()
    return TestClient(app)


def test_goal_status_completed_triggers_self_study(monkeypatch):
    calls: list[dict] = []

    async def _fake_trigger(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(autonomy_module, "maybe_trigger_self_study_on_goal_completion", _fake_trigger)
    client = _client()

    resp = client.patch("/api/v1/autonomy/goals/g-1/status", json={"status": "completed"})
    assert resp.status_code == 200
    assert len(calls) == 1
    assert calls[0]["trigger_type"] == "goal_completed"
    assert "g-1" in calls[0]["reason"]


def test_goal_status_non_completed_does_not_trigger_self_study(monkeypatch):
    calls: list[dict] = []

    async def _fake_trigger(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(autonomy_module, "maybe_trigger_self_study_on_goal_completion", _fake_trigger)
    client = _client()

    resp = client.patch("/api/v1/autonomy/goals/g-1/status", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert calls == []
