import os
import sys
from types import SimpleNamespace

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.autonomy.goal_manager import GoalStatus
from app.models.schemas import TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.collaboration_service import CollaborationService


class _FakeGoalManager:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def transition_status(self, goal_id: str, status: str, **_kwargs):
        self.calls.append((goal_id, status))
        return SimpleNamespace(id=goal_id, status=status)


def _make_state(status: str, goal_id: str | None) -> TaskState:
    meta = {}
    if goal_id is not None:
        meta = {"autonomy": {"goal_id": goal_id}}
    return TaskState(
        original_goal="Teste",
        next_agent_role="router",
        status=status,
        meta=meta,
        data_payload={},
        history=[],
    )


def test_maybe_finalize_autonomy_goal_marks_completed(monkeypatch):
    fake_goal_manager = _FakeGoalManager()
    import app.services.collaboration_service as collaboration_module
    monkeypatch.setattr(collaboration_module, "AutonomyGoalRepository", lambda: fake_goal_manager)

    service = CollaborationService(CollaborationRepository())
    state = _make_state(status="success", goal_id="goal-1")
    service.maybe_finalize_autonomy_goal(state)

    assert fake_goal_manager.calls == [("goal-1", GoalStatus.COMPLETED)]
    assert state.meta["autonomy"]["goal_completion_hook_applied"] is True
    assert state.meta["autonomy"]["goal_completion_from_task_status"] == "completed"


def test_maybe_finalize_autonomy_goal_marks_failed_for_terminal_error(monkeypatch):
    fake_goal_manager = _FakeGoalManager()
    import app.services.collaboration_service as collaboration_module
    monkeypatch.setattr(collaboration_module, "AutonomyGoalRepository", lambda: fake_goal_manager)

    service = CollaborationService(CollaborationRepository())
    state = _make_state(status="error", goal_id="goal-2")
    service.maybe_finalize_autonomy_goal(state)

    assert fake_goal_manager.calls == [("goal-2", GoalStatus.FAILED)]


def test_maybe_finalize_autonomy_goal_ignores_non_terminal_status(monkeypatch):
    fake_goal_manager = _FakeGoalManager()
    import app.services.collaboration_service as collaboration_module
    monkeypatch.setattr(collaboration_module, "AutonomyGoalRepository", lambda: fake_goal_manager)

    service = CollaborationService(CollaborationRepository())
    state = _make_state(status="in_progress", goal_id="goal-3")
    service.maybe_finalize_autonomy_goal(state)

    assert fake_goal_manager.calls == []


def test_maybe_finalize_autonomy_goal_is_idempotent_on_same_taskstate(monkeypatch):
    fake_goal_manager = _FakeGoalManager()
    import app.services.collaboration_service as collaboration_module
    monkeypatch.setattr(collaboration_module, "AutonomyGoalRepository", lambda: fake_goal_manager)

    service = CollaborationService(CollaborationRepository())
    state = _make_state(status="completed", goal_id="goal-4")
    service.maybe_finalize_autonomy_goal(state)
    service.maybe_finalize_autonomy_goal(state)

    assert fake_goal_manager.calls == [("goal-4", GoalStatus.COMPLETED)]
