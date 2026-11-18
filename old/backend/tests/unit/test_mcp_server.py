import os
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

if sys.version_info < (3, 10):
    pytest.skip("MCP server tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.autonomy.goal_manager import GoalManager

mcp_server = pytest.importorskip(
    "app.mcp.server", reason="pacote 'mcp' nao instalado neste ambiente"
)


class _FakeGoalRepo:
    def __init__(self):
        now = datetime.utcnow()
        self.rows = {
            "g1": SimpleNamespace(
                id="g1",
                title="Ativa",
                description="Meta ativa",
                priority=1,
                status="pending",
                success_criteria=None,
                deadline_ts=None,
                source="api",
                created_at=now,
                updated_at=now,
            ),
            "g2": SimpleNamespace(
                id="g2",
                title="Terminal",
                description="Meta concluida",
                priority=2,
                status="completed",
                success_criteria=None,
                deadline_ts=None,
                source="api",
                created_at=now,
                updated_at=now,
            ),
        }
        self.last_create_kwargs = None

    def list_goals(self, *, status=None, include_terminal=False, limit=None):
        rows = list(self.rows.values())
        if status:
            rows = [r for r in rows if r.status == status]
        elif not include_terminal:
            rows = [r for r in rows if r.status not in {"completed", "failed"}]
        return rows[:limit] if limit else rows

    def get_goal(self, goal_id):
        return self.rows.get(goal_id)

    def list_children(self, _goal_id):
        return []

    def create_goal(self, **kwargs):
        self.last_create_kwargs = kwargs
        now = datetime.utcnow()
        row = SimpleNamespace(
            id=kwargs["goal_id"],
            title=kwargs["title"],
            description=kwargs["description"],
            priority=kwargs["priority"],
            status="pending",
            success_criteria=kwargs.get("success_criteria"),
            deadline_ts=kwargs.get("deadline_ts"),
            source=kwargs.get("source", "api"),
            created_at=now,
            updated_at=now,
        )
        self.rows[row.id] = row
        return row


class _FakeAdminRepo:
    def __init__(self, *, state=None, running=None, runs=None):
        self._state = state or SimpleNamespace(last_studied_commit=None, last_success_at=None)
        self._running = running
        self._runs = runs or []

    def get_self_study_state(self):
        return self._state

    def get_latest_running_self_study(self):
        return self._running

    def list_self_study_runs(self, limit=20):
        return self._runs[:limit]


def _patch_goal_manager(monkeypatch, repo: _FakeGoalRepo):
    monkeypatch.setattr(
        mcp_server, "_goal_manager", lambda: GoalManager(memory_service=None, goal_repo=repo)
    )


def _patch_admin_repo(monkeypatch, repo: _FakeAdminRepo):
    monkeypatch.setattr(mcp_server, "_admin_repo", lambda: repo)


def test_list_active_goals_hides_terminal_by_default(monkeypatch):
    _patch_goal_manager(monkeypatch, _FakeGoalRepo())

    goals = mcp_server.list_active_goals()

    assert [g["id"] for g in goals] == ["g1"]
    assert goals[0]["status"] == "pending"


def test_get_goal_returns_terminal_goal(monkeypatch):
    _patch_goal_manager(monkeypatch, _FakeGoalRepo())

    goal = mcp_server.get_goal("g2")

    assert goal is not None
    assert goal["status"] == "completed"


def test_get_goal_returns_none_for_unknown_id(monkeypatch):
    _patch_goal_manager(monkeypatch, _FakeGoalRepo())

    assert mcp_server.get_goal("does-not-exist") is None


def test_propose_goal_sets_source_mcp(monkeypatch):
    repo = _FakeGoalRepo()
    _patch_goal_manager(monkeypatch, repo)

    goal = mcp_server.propose_goal(title="Investigar X", description="Descricao")

    assert goal["source"] == "mcp"
    assert repo.last_create_kwargs["source"] == "mcp"


def test_get_self_study_status_reports_running_and_recent_runs(monkeypatch):
    running = SimpleNamespace(id=7, status="running", mode="incremental")
    run = SimpleNamespace(id=6, status="success", mode="full", files_processed=3, files_total=3)
    repo = _FakeAdminRepo(
        state=SimpleNamespace(last_studied_commit="abc123", last_success_at=None),
        running=running,
        runs=[run],
    )
    _patch_admin_repo(monkeypatch, repo)

    status = mcp_server.get_self_study_status()

    assert status["last_studied_commit"] == "abc123"
    assert status["running"] == {"id": 7, "status": "running", "mode": "incremental"}
    assert status["recent_runs"] == [
        {"id": 6, "status": "success", "mode": "full", "files_processed": 3, "files_total": 3}
    ]


def test_get_self_study_status_running_none_when_idle(monkeypatch):
    repo = _FakeAdminRepo()
    _patch_admin_repo(monkeypatch, repo)

    status = mcp_server.get_self_study_status()

    assert status["running"] is None
    assert status["recent_runs"] == []


def test_list_self_study_runs_clamps_limit(monkeypatch):
    calls = {}

    class _Repo(_FakeAdminRepo):
        def list_self_study_runs(self, limit=20):
            calls["limit"] = limit
            return []

    _patch_admin_repo(monkeypatch, _Repo())

    mcp_server.list_self_study_runs(limit=10_000)

    assert calls["limit"] == 200


@pytest.mark.asyncio
async def test_get_autonomy_maturity_returns_score():
    result = await mcp_server.get_autonomy_maturity()

    assert "maturity_score" in result
    assert "max_score" in result
    assert result["max_score"] > 0
