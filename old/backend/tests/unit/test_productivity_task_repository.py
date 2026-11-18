from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.productivity_task_models import ProductivityTask
from app.repositories.productivity_task_repository import ProductivityTaskRepository


def test_repository_scopes_reads_and_transitions_to_owner() -> None:
    engine = create_engine("sqlite:///:memory:")
    ProductivityTask.__table__.create(engine)
    session = Session(engine)
    repository = ProductivityTaskRepository(session=session)

    repository.create_queued(
        task_id="task-1",
        owner_user_id=7,
        operation="google_calendar_add_event",
    )

    assert repository.get_owned(task_id="task-1", owner_user_id=8) is None
    running = repository.mark_running(task_id="task-1", owner_user_id=7)
    assert running is not None
    assert running.status == "running"
    assert running.started_at is not None
    completed = repository.mark_succeeded(
        task_id="task-1",
        owner_user_id=7,
        provider_resource_id="event-1",
    )
    assert completed is not None
    assert completed.status == "succeeded"
    assert completed.provider_resource_id == "event-1"
    assert completed.completed_at is not None

    session.close()
