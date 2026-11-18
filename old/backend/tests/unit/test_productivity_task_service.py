from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services.productivity_task_service import (
    ProductivityTaskNotFoundError,
    ProductivityTaskPersistenceError,
    ProductivityTaskService,
)


def _row(status: str = "queued") -> SimpleNamespace:
    return SimpleNamespace(
        task_id="task-1",
        operation="google_mail_send",
        status=status,
        provider_resource_id=None,
        error_code=None,
        error_message=None,
        created_at=datetime(2026, 8, 14),
        updated_at=datetime(2026, 8, 14),
        started_at=None,
        completed_at=None,
    )


class _Repository:
    def __init__(self, row: SimpleNamespace | None = None) -> None:
        self.row = row
        self.created = False

    def create_queued(self, **_kwargs: object) -> SimpleNamespace:
        self.created = True
        self.row = _row()
        return self.row

    def get_owned(self, **_kwargs: object) -> SimpleNamespace | None:
        return self.row

    def mark_running(self, **_kwargs: object) -> SimpleNamespace | None:
        if self.row is not None and self.row.status != "succeeded":
            self.row.status = "running"
        return self.row

    def mark_succeeded(self, **kwargs: object) -> SimpleNamespace | None:
        if self.row is not None:
            self.row.status = "succeeded"
            self.row.provider_resource_id = kwargs["provider_resource_id"]
        return self.row

    def mark_failed(self, **kwargs: object) -> SimpleNamespace | None:
        if self.row is not None:
            self.row.status = "failed"
            self.row.error_code = kwargs["error_code"]
        return self.row


def test_start_or_create_supports_messages_queued_before_schema_rollout() -> None:
    repository = _Repository()
    service = ProductivityTaskService(repository=repository)  # type: ignore[arg-type]

    assert service.start_or_create(
        task_id="task-1",
        owner_user_id=7,
        operation="google_mail_send",
    )
    assert repository.created is True
    assert repository.row is not None
    assert repository.row.status == "running"


def test_succeeded_redelivery_is_not_executed_again() -> None:
    service = ProductivityTaskService(repository=_Repository(_row("succeeded")))  # type: ignore[arg-type]

    assert not service.start_or_create(
        task_id="task-1",
        owner_user_id=7,
        operation="google_mail_send",
    )


def test_get_owned_returns_typed_snapshot_without_payload() -> None:
    snapshot = ProductivityTaskService(repository=_Repository(_row())).get_owned(  # type: ignore[arg-type]
        task_id="task-1",
        owner_user_id=7,
    )

    assert snapshot.task_id == "task-1"
    assert snapshot.status == "queued"
    assert snapshot.created_at is not None
    assert snapshot.created_at.tzinfo is UTC
    assert not hasattr(snapshot, "payload")


def test_missing_task_and_repository_failure_are_distinct() -> None:
    service = ProductivityTaskService(repository=_Repository())  # type: ignore[arg-type]
    with pytest.raises(ProductivityTaskNotFoundError):
        service.get_owned(task_id="missing", owner_user_id=7)

    class _BrokenRepository(_Repository):
        def get_owned(self, **_kwargs: object) -> SimpleNamespace | None:
            raise RuntimeError("database offline")

    with pytest.raises(ProductivityTaskPersistenceError):
        ProductivityTaskService(repository=_BrokenRepository()).get_owned(  # type: ignore[arg-type]
            task_id="task-1",
            owner_user_id=7,
        )
