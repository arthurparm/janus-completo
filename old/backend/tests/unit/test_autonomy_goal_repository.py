import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.models.autonomy_models import AutonomyGoal, AutonomyGoalTransition
from app.models.config_models import Base
from app.repositories.autonomy_goal_repository import AutonomyGoalRepository


@pytest.fixture
def goal_repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[AutonomyGoal.__table__, AutonomyGoalTransition.__table__],
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield AutonomyGoalRepository(session=session), session
    finally:
        session.close()


def test_goal_repository_create_and_get_next_pending(goal_repo):
    repo, _ = goal_repo
    repo.create_goal(
        goal_id="g1",
        title="Meta 1",
        description="Desc 1",
        priority=5,
        source="api",
    )
    repo.create_goal(
        goal_id="g2",
        title="Meta 2",
        description="Desc 2",
        priority=1,
        source="api",
    )

    next_goal = repo.get_next_pending_goal()
    assert next_goal is not None
    assert next_goal.id == "g2"


def test_goal_repository_transition_status_is_idempotent_and_records_transition(goal_repo):
    repo, _ = goal_repo
    repo.create_goal(
        goal_id="g1",
        title="Meta 1",
        description="Desc 1",
        priority=3,
        source="api",
    )

    first = repo.transition_status(
        "g1",
        "in_progress",
        reason="selected",
        actor="autonomy_loop",
    )
    second = repo.transition_status(
        "g1",
        "in_progress",
        reason="selected-again",
        actor="autonomy_loop",
    )

    assert first is not None
    assert second is not None
    assert first.status == "in_progress"
    assert second.status == "in_progress"

    transitions = repo.list_transitions("g1")
    assert len(transitions) == 2  # created -> pending, then pending -> in_progress (no duplicate)
    assert transitions[0].to_status == "pending"
    assert transitions[1].to_status == "in_progress"
    assert transitions[1].actor == "autonomy_loop"


def test_goal_repository_list_goals_hides_terminal_when_requested(goal_repo):
    repo, _ = goal_repo
    repo.create_goal(goal_id="g1", title="A", description="A", priority=1)
    repo.create_goal(goal_id="g2", title="B", description="B", priority=2)
    repo.transition_status("g2", "completed", actor="api", reason="done")

    active_only = repo.list_goals(include_terminal=False)
    all_rows = repo.list_goals(include_terminal=True)
    completed_rows = repo.list_goals(status="completed")

    assert [r.id for r in active_only] == ["g1"]
    assert {r.id for r in all_rows} == {"g1", "g2"}
    assert [r.id for r in completed_rows] == ["g2"]


def test_goal_repository_delete_goal_cascades_transitions(goal_repo):
    repo, session = goal_repo
    repo.create_goal(goal_id="g1", title="A", description="A", priority=1)
    repo.transition_status("g1", "failed", actor="collaboration_hook", task_id="task-1")

    assert repo.delete_goal("g1") is True
    assert repo.get_goal("g1") is None
    assert session.query(AutonomyGoalTransition).filter_by(goal_id="g1").count() == 0
    assert repo.delete_goal("g1") is False
