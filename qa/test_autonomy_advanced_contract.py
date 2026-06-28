import pytest
from httpx import ASGITransport, AsyncClient

AUTONOMY_GOAL_GET_REF = "/api/v1/autonomy/goals/{goal_id}"
AUTONOMY_GOAL_STATUS_REF = "/api/v1/autonomy/goals/{goal_id}/status"
AUTONOMY_GOAL_DELETE_REF = "/api/v1/autonomy/goals/{goal_id}"
AUTONOMY_GOAL_METRICS_REF = "/api/v1/autonomy/goals/{goal_id}/metrics"
AUTONOMY_GOALS_LIST_REF = "/api/v1/autonomy/goals"
AUTONOMY_GOALS_CREATE_REF = "/api/v1/autonomy/goals"
AUTONOMY_START_REF = "/api/v1/autonomy/start"
AUTONOMY_STOP_REF = "/api/v1/autonomy/stop"
AUTONOMY_STATUS_REF = "/api/v1/autonomy/status"
AUTONOMY_PLAN_GET_REF = "/api/v1/autonomy/plan"
AUTONOMY_PLAN_PUT_REF = "/api/v1/autonomy/plan"
AUTONOMY_POLICY_PUT_REF = "/api/v1/autonomy/policy"
AUTONOMY_HEALTH_REF = "/api/v1/autonomy/health"
AUTONOMY_MATURITY_REF = "/api/v1/autonomy/maturity"
AUTONOMY_HISTORY_RUN_REF = "/api/v1/autonomy/history/runs/{run_id}"
AUTONOMY_HISTORY_STEPS_REF = "/api/v1/autonomy/history/runs/{run_id}/steps"
AUTONOMY_HISTORY_ENQUEUES_REF = "/api/v1/autonomy/history/runs/{run_id}/enqueues"
AUTONOMY_ADMIN_BACKLOG_SYNC_REF = "/api/v1/autonomy/admin/backlog/sync"
AUTONOMY_ADMIN_BOARD_REF = "/api/v1/autonomy/admin/board"
AUTONOMY_ADMIN_SELF_STUDY_RUN_REF = "/api/v1/autonomy/admin/self-study/run"
AUTONOMY_ADMIN_SELF_STUDY_STATUS_REF = "/api/v1/autonomy/admin/self-study/status"
AUTONOMY_ADMIN_SELF_STUDY_RUNS_REF = "/api/v1/autonomy/admin/self-study/runs"


@pytest.fixture
def async_client(monkeypatch):
    import sys
    import types

    sys.modules.pop("app.core.infrastructure.message_broker", None)
    message_broker_stub = types.ModuleType("app.core.infrastructure.message_broker")

    def get_broker(*_args, **_kwargs):
        return None

    message_broker_stub.get_broker = get_broker
    monkeypatch.setitem(sys.modules, "app.core.infrastructure.message_broker", message_broker_stub)

    from fastapi import FastAPI, Request

    from app.api.v1.endpoints import autonomy as autonomy_endpoint
    from app.api.v1.endpoints import autonomy_admin as autonomy_admin_endpoint
    from app.api.v1.endpoints import autonomy_history as autonomy_history_endpoint
    from app.config import settings
    from app.core.infrastructure.auth import create_token, get_actor_user_id

    app = FastAPI()

    @app.middleware("http")
    async def actor_binding(request: Request, call_next):
        actor = get_actor_user_id(request)
        request.state.actor_user_id = str(actor) if actor is not None else None
        request.state.actor_project_id = (request.headers.get("X-Project-Id") or "").strip() or None
        return await call_next(request)

    app.include_router(autonomy_endpoint.router, prefix="/api/v1/autonomy")
    app.include_router(autonomy_history_endpoint.router, prefix="/api/v1/autonomy/history")
    app.include_router(autonomy_admin_endpoint.router, prefix="/api/v1/autonomy/admin")

    from app.core.autonomy.goal_manager import GoalStatus, get_goal_manager
    from app.api.v1.endpoints.autonomy_history import get_autonomy_repo
    from app.repositories import user_repository
    from app.services.autonomy_admin_service import get_autonomy_admin_service
    from app.services.autonomy_service import get_autonomy_service

    class GoalObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class DummyGoalManager:
        def __init__(self):
            self._goals = {
                "g1": GoalObj(
                    id="g1",
                    title="T",
                    description="D",
                    priority=5,
                    status=GoalStatus.PENDING,
                    success_criteria=None,
                    deadline_ts=None,
                    created_at=1.0,
                    updated_at=1.0,
                )
            }

        def get_goal(self, goal_id: str):
            return self._goals.get(goal_id)

        def update_goal_status(self, goal_id: str, status: str, **_kwargs):
            goal = self._goals.get(goal_id)
            if not goal:
                return None
            goal.status = status
            goal.updated_at = 2.0
            return goal

        def delete_goal(self, goal_id: str) -> bool:
            return bool(self._goals.pop(goal_id, None))

        def list_goals(self, status: str | None = None):
            if status is None:
                return list(self._goals.values())
            return [g for g in self._goals.values() if g.status == status]

        def create_goal(self, **kwargs):
            goal = GoalObj(
                id=kwargs.get("id") or "g2",
                title=kwargs.get("title"),
                description=kwargs.get("description"),
                priority=int(kwargs.get("priority") or 5),
                status=kwargs.get("status") or GoalStatus.PENDING,
                success_criteria=kwargs.get("success_criteria"),
                deadline_ts=kwargs.get("deadline_ts"),
                created_at=kwargs.get("created_at") or 1.0,
                updated_at=kwargs.get("updated_at") or 1.0,
            )
            self._goals[str(goal.id)] = goal
            return goal

    class RunObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class StepObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class EnqueueObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class DummyAutonomyRepo:
        def list_runs(self, project_id=None, limit=50):
            return [
                RunObj(
                    id=1,
                    project_id=project_id,
                    status="running",
                    cycles=3,
                    started_at="2023-01-01",
                    stopped_at=None,
                )
            ][:limit]

        def get_run(self, run_id: int):
            if run_id != 1:
                return None
            return RunObj(
                id=1,
                project_id=None,
                status="running",
                cycles=3,
                started_at="2023-01-01",
                stopped_at=None,
            )

        def list_steps(self, run_id: int, cycle: int | None = None, limit: int = 100):
            if run_id != 1:
                return []
            items = [
                StepObj(
                    id=10,
                    cycle=1,
                    tool="tool_x",
                    input_preview="{}",
                    input_length=2,
                    result_preview="{}",
                    result_length=2,
                    success=1,
                    error=None,
                    duration_seconds=0.01,
                    created_at="2023-01-01",
                )
            ]
            if cycle is not None:
                items = [it for it in items if int(it.cycle) == int(cycle)]
            return items[:limit]

        def list_enqueues(self, run_id: int, limit: int = 100):
            if run_id != 1:
                return []
            return [
                EnqueueObj(
                    id=99,
                    run_id=1,
                    goal_id="g1",
                    task_id="t1",
                    cycle=1,
                    selected_tool="tool_x",
                    idempotency_key="k1",
                    publish_status="published",
                    publish_error=None,
                    created_at="2023-01-01",
                    updated_at="2023-01-01",
                )
            ][:limit]

    class DummyAutonomyAdminService:
        async def sync_backlog(self):
            return {
                "created": 0,
                "deduped": 0,
                "capped": 0,
                "closed": 0,
                "fallback_used_count": 0,
                "findings_total": 0,
            }

        def get_board(self, status=None, limit=200):
            return [
                {"id": "b1", "status": status or "open", "title": "T", "priority": 5}
            ][:limit]

        async def run_self_study(self, mode: str, reason: str | None, trigger_type: str):
            return {"status": "ok", "mode": mode, "reason": reason, "trigger_type": trigger_type}

        def get_self_study_status(self):
            return {"active": False, "last_run_at": None}

        def list_self_study_runs(self, limit: int = 20):
            return [{"id": "r1", "mode": "incremental"}][:limit]

    app.dependency_overrides[get_goal_manager] = lambda: DummyGoalManager()
    app.dependency_overrides[get_autonomy_repo] = lambda: DummyAutonomyRepo()
    class DummyAutonomyService:
        async def start(self, _config):
            return True

        async def stop(self):
            return True

        def get_status(self):
            return {
                "active": True,
                "cycle_count": 0,
                "last_cycle_at": None,
                "config": {
                    "interval_seconds": 60,
                    "risk_profile": "balanced",
                    "auto_confirm": False,
                    "allowlist": [],
                    "blocklist": [],
                    "max_actions_per_cycle": 10,
                    "max_seconds_per_cycle": 60,
                    "execution_mode": "SAFE",
                    "plan": [],
                },
                "runtime_lock": None,
            }

        def update_plan(self, plan):
            return True

        def update_policy_config(self, **_kwargs):
            return True

    app.dependency_overrides[get_autonomy_service] = lambda: DummyAutonomyService()
    app.dependency_overrides[get_autonomy_admin_service] = lambda: DummyAutonomyAdminService()

    monkeypatch.setattr(user_repository.UserRepository, "is_admin", lambda _self, _user_id: True)
    monkeypatch.setattr(user_repository.UserRepository, "has_role", lambda _self, _user_id, _role_name: False)
    monkeypatch.setattr(autonomy_endpoint, "record_audit_event_direct", lambda **_kwargs: None)

    headers = {"Authorization": f"Bearer {create_token(1, expires_in=3600)}"}
    if getattr(settings, "PUBLIC_API_KEY", None):
        headers["X-API-Key"] = str(settings.PUBLIC_API_KEY)

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers)
    yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAutonomyGoalsContract:
    async def test_goals_list_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/goals")
        assert resp.status_code == 200

    async def test_goals_create_ok(self, async_client):
        resp = await async_client.post(
            "/api/v1/autonomy/goals",
            json={"title": "T2", "description": "D2", "priority": 5},
        )
        assert resp.status_code == 200

    async def test_goal_get_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/goals/g1")
        assert resp.status_code == 200

    async def test_goal_get_404(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/goals/missing")
        assert resp.status_code == 404

    async def test_goal_patch_status_ok(self, async_client):
        resp = await async_client.patch(
            "/api/v1/autonomy/goals/g1/status",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200

    async def test_goal_patch_status_invalid(self, async_client):
        resp = await async_client.patch(
            "/api/v1/autonomy/goals/g1/status",
            json={"status": "nope"},
        )
        assert resp.status_code == 422

    async def test_goal_patch_status_404(self, async_client):
        resp = await async_client.patch(
            "/api/v1/autonomy/goals/missing/status",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 404

    async def test_goal_delete_ok(self, async_client):
        resp = await async_client.delete("/api/v1/autonomy/goals/g1")
        assert resp.status_code == 200

    async def test_goal_delete_404(self, async_client):
        resp = await async_client.delete("/api/v1/autonomy/goals/missing")
        assert resp.status_code == 404

    async def test_goal_metrics_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/goals/g1/metrics")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("goal_id") == "g1"


@pytest.mark.asyncio
class TestAutonomyLoopContract:
    async def test_autonomy_start(self, async_client):
        resp = await async_client.post("/api/v1/autonomy/start", json={"interval_seconds": 60})
        assert resp.status_code == 200

    async def test_autonomy_status(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/status")
        assert resp.status_code == 200

    async def test_autonomy_plan_get(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/plan")
        assert resp.status_code == 200

    async def test_autonomy_plan_put(self, async_client):
        resp = await async_client.put("/api/v1/autonomy/plan", json={"plan": []})
        assert resp.status_code == 200

    async def test_autonomy_policy_put(self, async_client):
        resp = await async_client.put("/api/v1/autonomy/policy", json={})
        assert resp.status_code == 200

    async def test_autonomy_stop(self, async_client):
        resp = await async_client.post("/api/v1/autonomy/stop")
        assert resp.status_code == 200

    async def test_autonomy_health_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert "overall_status" in payload

    async def test_autonomy_maturity_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/maturity")
        assert resp.status_code == 200
        payload = resp.json()
        assert "maturity_score" in payload


@pytest.mark.asyncio
class TestAutonomyHistoryContract:
    async def test_history_list_runs(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/history/runs")
        assert resp.status_code == 200

    async def test_history_get_run_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/history/runs/1")
        assert resp.status_code == 200

    async def test_history_get_run_404(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/history/runs/2")
        assert resp.status_code == 404

    async def test_history_steps_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/history/runs/1/steps")
        assert resp.status_code == 200

    async def test_history_enqueues_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/history/runs/1/enqueues")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestAutonomyAdminContract:
    async def test_admin_backlog_sync_ok(self, async_client):
        resp = await async_client.post("/api/v1/autonomy/admin/backlog/sync")
        assert resp.status_code == 200

    async def test_admin_board_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/admin/board")
        assert resp.status_code == 200

    async def test_admin_self_study_run_ok(self, async_client):
        resp = await async_client.post(
            "/api/v1/autonomy/admin/self-study/run",
            json={"mode": "incremental", "reason": "contract-test"},
        )
        assert resp.status_code == 200

    async def test_admin_self_study_status_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/admin/self-study/status")
        assert resp.status_code == 200

    async def test_admin_self_study_runs_ok(self, async_client):
        resp = await async_client.get("/api/v1/autonomy/admin/self-study/runs")
        assert resp.status_code == 200
