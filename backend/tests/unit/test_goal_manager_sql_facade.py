import os
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.autonomy.goal_manager import GoalManager, GoalStatus


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
                created_at=now,
                updated_at=now,
            ),
        }

    def list_goals(self, *, status=None, include_terminal=False, limit=None):
        rows = list(self.rows.values())
        if status:
            rows = [r for r in rows if r.status == status]
        elif not include_terminal:
            rows = [r for r in rows if r.status not in {"completed", "failed"}]
        return rows[:limit] if limit else rows

    def get_goal(self, goal_id):
        return self.rows.get(goal_id)

    def get_next_pending_goal(self):
        pending = [r for r in self.rows.values() if r.status == "pending"]
        return pending[0] if pending else None

    def create_goal(self, **kwargs):
        now = datetime.utcnow()
        row = SimpleNamespace(
            id=kwargs["goal_id"],
            title=kwargs["title"],
            description=kwargs["description"],
            priority=kwargs["priority"],
            status="pending",
            success_criteria=kwargs.get("success_criteria"),
            deadline_ts=kwargs.get("deadline_ts"),
            created_at=now,
            updated_at=now,
        )
        self.rows[row.id] = row
        return row

    def transition_status(self, goal_id, status, **_kwargs):
        row = self.rows.get(goal_id)
        if not row:
            return None
        row.status = status
        row.updated_at = datetime.utcnow()
        return row

    def delete_goal(self, goal_id):
        return self.rows.pop(goal_id, None) is not None


def test_goal_manager_list_hides_terminal_by_default_but_get_keeps_terminal():
    manager = GoalManager(memory_service=None, goal_repo=_FakeGoalRepo())

    listed = manager.list_goals()
    assert [g.id for g in listed] == ["g1"]

    completed = manager.get_goal("g2")
    assert completed is not None
    assert completed.status == GoalStatus.COMPLETED


def test_goal_manager_update_goal_status_persists_terminal_in_repo():
    repo = _FakeGoalRepo()
    manager = GoalManager(memory_service=None, goal_repo=repo)

    updated = manager.update_goal_status("g1", GoalStatus.FAILED, actor="api")
    assert updated is not None
    assert updated.status == GoalStatus.FAILED

    assert manager.get_goal("g1") is not None
    assert manager.list_goals() == []
    assert [g.id for g in manager.list_goals(status=GoalStatus.FAILED)] == ["g1"]
