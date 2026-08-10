from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import db
from app.models.chat_study_models import ChatStudyRun
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ChatStudyRepositoryError(RuntimeError):
    pass


class ChatStudyTransitionConflict(ChatStudyRepositoryError):
    pass


@dataclass(frozen=True)
class ChatStudyRunState:
    job_id: str
    owner_user_id: str
    conversation_id: str
    message_id: str
    question: str
    status: str
    progress: int
    version: int
    worker_token: str | None
    lease_until: float | None
    placeholder_message: str | None
    failure_classification: str | None
    final_response: dict[str, Any] | None
    error: str | None
    created_at: float
    updated_at: float


class ChatStudyRepository:
    def __init__(
        self,
        *,
        session: Session | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        if session is not None and session_factory is not None:
            raise ValueError("Provide either session or session_factory, not both")
        self._session = session
        self._session_factory = session_factory

    def _open_session(self) -> tuple[Session, bool]:
        if self._session is not None:
            return self._session, False
        if self._session_factory is not None:
            return self._session_factory(), True
        return db.get_session_direct(), True

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _snapshot(run: ChatStudyRun) -> ChatStudyRunState:
        return ChatStudyRunState(
            job_id=str(run.id),
            owner_user_id=str(run.owner_user_id),
            conversation_id=str(run.conversation_id),
            message_id=str(run.message_id),
            question=str(run.question),
            status=str(run.status),
            progress=int(run.progress or 0),
            version=int(run.version or 1),
            worker_token=str(run.worker_token) if run.worker_token else None,
            lease_until=run.lease_until.timestamp() if run.lease_until else None,
            placeholder_message=(
                str(run.placeholder_message) if run.placeholder_message else None
            ),
            failure_classification=(
                str(run.failure_classification) if run.failure_classification else None
            ),
            final_response=(
                dict(run.final_response_json) if run.final_response_json else None
            ),
            error=str(run.error) if run.error else None,
            created_at=run.created_at.timestamp(),
            updated_at=run.updated_at.timestamp(),
        )

    def create_pending(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        conversation_id: str,
        message_id: str,
        question: str,
        request_fingerprint: str,
        placeholder_message: str,
    ) -> ChatStudyRunState:
        session, should_close = self._open_session()
        try:
            run = ChatStudyRun(
                id=job_id,
                owner_user_id=owner_user_id,
                conversation_id=conversation_id,
                message_id=message_id,
                question=question,
                request_fingerprint=request_fingerprint,
                status="pending",
                progress=5,
                version=1,
                placeholder_message=placeholder_message,
            )
            session.add(run)
            try:
                session.commit()
                session.refresh(run)
                return self._snapshot(run)
            except IntegrityError:
                session.rollback()
                existing = (
                    session.query(ChatStudyRun)
                    .filter(
                        ChatStudyRun.owner_user_id == owner_user_id,
                        ChatStudyRun.conversation_id == conversation_id,
                        ChatStudyRun.message_id == message_id,
                    )
                    .one()
                )
                if str(existing.request_fingerprint) != request_fingerprint:
                    raise ChatStudyRepositoryError(
                        "Study message already exists with a different question"
                    )
                return self._snapshot(existing)
        finally:
            if should_close:
                session.close()

    def get(self, job_id: str) -> ChatStudyRunState | None:
        session, should_close = self._open_session()
        try:
            run = session.query(ChatStudyRun).filter(ChatStudyRun.id == job_id).one_or_none()
            return self._snapshot(run) if run is not None else None
        finally:
            if should_close:
                session.close()

    def claim(
        self,
        *,
        job_id: str,
        worker_token: str,
        lease_seconds: int,
    ) -> ChatStudyRunState | None:
        session, should_close = self._open_session()
        try:
            now = self._utcnow()
            updated = (
                session.query(ChatStudyRun)
                .filter(
                    ChatStudyRun.id == job_id,
                    or_(
                        ChatStudyRun.status == "pending",
                        and_(
                            ChatStudyRun.status == "running",
                            ChatStudyRun.lease_until < now,
                        ),
                    ),
                )
                .update(
                    {
                        ChatStudyRun.status: "running",
                        ChatStudyRun.worker_token: worker_token,
                        ChatStudyRun.lease_until: now
                        + timedelta(seconds=max(1, lease_seconds)),
                        ChatStudyRun.version: ChatStudyRun.version + 1,
                        ChatStudyRun.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            if int(updated or 0) != 1:
                return None
            run = session.query(ChatStudyRun).filter(ChatStudyRun.id == job_id).one()
            return self._snapshot(run)
        finally:
            if should_close:
                session.close()

    def transition(
        self,
        *,
        job_id: str,
        from_states: Iterable[str],
        to_state: str,
        progress: int | None = None,
        placeholder_message: str | None = None,
        failure_classification: str | None = None,
        final_response: dict[str, Any] | None = None,
        error: str | None = None,
        worker_token: str | None = None,
        lease_seconds: int | None = None,
    ) -> ChatStudyRunState:
        session, should_close = self._open_session()
        try:
            run = (
                session.query(ChatStudyRun)
                .filter(ChatStudyRun.id == job_id)
                .with_for_update()
                .one_or_none()
            )
            if run is None:
                raise ChatStudyRepositoryError("Study job not found")
            if worker_token is not None and str(run.worker_token or "") != worker_token:
                raise ChatStudyTransitionConflict("Study job lease is owned by another worker")
            if str(run.status) not in set(from_states):
                if str(run.status) == to_state:
                    return self._snapshot(run)
                raise ChatStudyTransitionConflict(
                    f"Cannot transition study job from {run.status} to {to_state}"
                )
            run.status = to_state
            if progress is not None:
                run.progress = max(0, min(100, int(progress)))
            if placeholder_message is not None:
                run.placeholder_message = placeholder_message
            run.failure_classification = failure_classification
            run.final_response_json = final_response
            run.error = error
            if lease_seconds is not None:
                run.lease_until = self._utcnow() + timedelta(
                    seconds=max(1, lease_seconds)
                )
            run.version = int(run.version or 0) + 1
            run.updated_at = self._utcnow()
            if to_state in {"completed", "failed", "cancelled"}:
                run.completed_at = self._utcnow()
                run.worker_token = None
                run.lease_until = None
            session.commit()
            session.refresh(run)
            return self._snapshot(run)
        finally:
            if should_close:
                session.close()
