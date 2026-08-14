from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from app.repositories.productivity_task_repository import ProductivityTaskRepository

ProductivityTaskStatus = Literal["queued", "running", "succeeded", "failed"]
ProductivityTaskOperation = Literal["google_calendar_add_event", "google_mail_send"]


class ProductivityTaskPersistenceError(RuntimeError):
    """The durable productivity task lifecycle is unavailable."""


class ProductivityTaskNotFoundError(LookupError):
    """No task owned by the actor has the supplied identifier."""


@dataclass(frozen=True, slots=True)
class ProductivityTaskSnapshot:
    task_id: str
    operation: ProductivityTaskOperation
    status: ProductivityTaskStatus
    provider_resource_id: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None


def _as_utc(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _snapshot(row: object) -> ProductivityTaskSnapshot:
    operation = str(getattr(row, "operation", ""))
    if operation not in {"google_calendar_add_event", "google_mail_send"}:
        raise ProductivityTaskPersistenceError("Invalid productivity task operation")
    status = str(getattr(row, "status", ""))
    if status not in {"queued", "running", "succeeded", "failed"}:
        raise ProductivityTaskPersistenceError("Invalid productivity task status")
    return ProductivityTaskSnapshot(
        task_id=str(getattr(row, "task_id")),
        operation=cast(ProductivityTaskOperation, operation),
        status=cast(ProductivityTaskStatus, status),
        provider_resource_id=getattr(row, "provider_resource_id", None),
        error_code=getattr(row, "error_code", None),
        error_message=getattr(row, "error_message", None),
        created_at=_as_utc(getattr(row, "created_at", None)),
        updated_at=_as_utc(getattr(row, "updated_at", None)),
        started_at=_as_utc(getattr(row, "started_at", None)),
        completed_at=_as_utc(getattr(row, "completed_at", None)),
    )


class ProductivityTaskService:
    def __init__(self, repository: ProductivityTaskRepository | None = None) -> None:
        self._repository = repository or ProductivityTaskRepository()

    def create_queued(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        operation: ProductivityTaskOperation,
    ) -> None:
        try:
            self._repository.create_queued(
                task_id=task_id,
                owner_user_id=owner_user_id,
                operation=operation,
            )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not persist queued productivity task"
            ) from exc

    def start(self, *, task_id: str, owner_user_id: int) -> bool:
        try:
            row = self._repository.mark_running(
                task_id=task_id,
                owner_user_id=owner_user_id,
            )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not start productivity task"
            ) from exc
        if row is None:
            raise ProductivityTaskNotFoundError(task_id)
        return str(row.status) != "succeeded"

    def start_or_create(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        operation: ProductivityTaskOperation,
    ) -> bool:
        """Start a task, creating lifecycle state for pre-deployment queue messages."""
        try:
            row = self._repository.mark_running(
                task_id=task_id,
                owner_user_id=owner_user_id,
            )
            if row is None:
                self._repository.create_queued(
                    task_id=task_id,
                    owner_user_id=owner_user_id,
                    operation=operation,
                )
                row = self._repository.mark_running(
                    task_id=task_id,
                    owner_user_id=owner_user_id,
                )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not start productivity task"
            ) from exc
        if row is None:
            raise ProductivityTaskPersistenceError("Productivity task was not persisted")
        return str(row.status) != "succeeded"

    def succeed(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        provider_resource_id: str | None,
    ) -> None:
        try:
            row = self._repository.mark_succeeded(
                task_id=task_id,
                owner_user_id=owner_user_id,
                provider_resource_id=provider_resource_id,
            )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not complete productivity task"
            ) from exc
        if row is None:
            raise ProductivityTaskNotFoundError(task_id)

    def fail(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        error_code: str,
    ) -> None:
        try:
            row = self._repository.mark_failed(
                task_id=task_id,
                owner_user_id=owner_user_id,
                error_code=error_code,
                error_message="The external productivity effect failed",
            )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not persist productivity task failure"
            ) from exc
        if row is None:
            raise ProductivityTaskNotFoundError(task_id)

    def get_owned(self, *, task_id: str, owner_user_id: int) -> ProductivityTaskSnapshot:
        try:
            row = self._repository.get_owned(
                task_id=task_id,
                owner_user_id=owner_user_id,
            )
        except Exception as exc:
            raise ProductivityTaskPersistenceError(
                "Could not read productivity task"
            ) from exc
        if row is None:
            raise ProductivityTaskNotFoundError(task_id)
        return _snapshot(row)
