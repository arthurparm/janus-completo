from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from app.db import db
from app.models.productivity_task_models import ProductivityTask


class ProductivityTaskRepository:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _get_session(self) -> Session:
        return self._session or db.get_session_direct()

    def _finish(self, session: Session) -> None:
        if self._session is None:
            session.close()

    def create_queued(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        operation: str,
    ) -> ProductivityTask:
        session = self._get_session()
        try:
            row = ProductivityTask(
                task_id=task_id,
                owner_user_id=owner_user_id,
                operation=operation,
                status="queued",
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            self._finish(session)

    def get_owned(self, *, task_id: str, owner_user_id: int) -> ProductivityTask | None:
        session = self._get_session()
        try:
            return cast(
                ProductivityTask | None,
                session.query(ProductivityTask)
                .filter(
                    ProductivityTask.task_id == task_id,
                    ProductivityTask.owner_user_id == owner_user_id,
                )
                .first(),
            )
        finally:
            self._finish(session)

    def mark_running(self, *, task_id: str, owner_user_id: int) -> ProductivityTask | None:
        session = self._get_session()
        try:
            row = cast(
                ProductivityTask | None,
                session.query(ProductivityTask)
                .filter(
                    ProductivityTask.task_id == task_id,
                    ProductivityTask.owner_user_id == owner_user_id,
                )
                .first(),
            )
            if row is None or row.status == "succeeded":
                return row
            row.status = "running"
            row.started_at = datetime.now(UTC).replace(tzinfo=None)
            row.completed_at = None
            row.error_code = None
            row.error_message = None
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            self._finish(session)

    def mark_succeeded(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        provider_resource_id: str | None,
    ) -> ProductivityTask | None:
        return self._mark_terminal(
            task_id=task_id,
            owner_user_id=owner_user_id,
            status="succeeded",
            provider_resource_id=provider_resource_id,
            error_code=None,
            error_message=None,
        )

    def mark_failed(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        error_code: str,
        error_message: str,
    ) -> ProductivityTask | None:
        return self._mark_terminal(
            task_id=task_id,
            owner_user_id=owner_user_id,
            status="failed",
            provider_resource_id=None,
            error_code=error_code[:128],
            error_message=error_message[:512],
        )

    def _mark_terminal(
        self,
        *,
        task_id: str,
        owner_user_id: int,
        status: str,
        provider_resource_id: str | None,
        error_code: str | None,
        error_message: str | None,
    ) -> ProductivityTask | None:
        session = self._get_session()
        try:
            row = cast(
                ProductivityTask | None,
                session.query(ProductivityTask)
                .filter(
                    ProductivityTask.task_id == task_id,
                    ProductivityTask.owner_user_id == owner_user_id,
                )
                .first(),
            )
            if row is None:
                return None
            row.status = status
            row.provider_resource_id = provider_resource_id
            row.error_code = error_code
            row.error_message = error_message
            row.completed_at = datetime.now(UTC).replace(tzinfo=None)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            self._finish(session)
