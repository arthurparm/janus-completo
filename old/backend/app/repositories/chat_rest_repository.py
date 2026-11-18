from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import db
from app.models.chat_rest_models import ChatRestRun
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ChatRestRepositoryError(RuntimeError):
    pass


class ChatRestIdempotencyConflict(ChatRestRepositoryError):
    pass


@dataclass(frozen=True)
class ChatRestRunState:
    id: str
    owner_user_id: str
    conversation_id: str
    request_id: str
    request_fingerprint: str
    status: str
    producer_token: str | None
    result: dict[str, Any] | None
    error_code: str | None

    @property
    def terminal(self) -> bool:
        return self.status in {"completed", "failed"}


class ChatRestRepository:
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
    def _snapshot(run: ChatRestRun) -> ChatRestRunState:
        return ChatRestRunState(
            id=str(run.id),
            owner_user_id=str(run.owner_user_id),
            conversation_id=str(run.conversation_id),
            request_id=str(run.request_id),
            request_fingerprint=str(run.request_fingerprint),
            status=str(run.status),
            producer_token=str(run.producer_token) if run.producer_token else None,
            result=dict(run.result_json) if run.result_json else None,
            error_code=str(run.error_code) if run.error_code else None,
        )

    def begin_or_get(
        self,
        *,
        owner_user_id: str,
        conversation_id: str,
        request_id: str,
        request_fingerprint: str,
        retention_hours: int,
    ) -> tuple[ChatRestRunState, bool]:
        session, should_close = self._open_session()
        try:
            existing = (
                session.query(ChatRestRun)
                .filter(
                    ChatRestRun.owner_user_id == owner_user_id,
                    ChatRestRun.conversation_id == conversation_id,
                    ChatRestRun.request_id == request_id,
                )
                .one_or_none()
            )
            if existing is not None:
                if str(existing.request_fingerprint) != request_fingerprint:
                    raise ChatRestIdempotencyConflict(
                        "Idempotency key was already used with a different request"
                    )
                return self._snapshot(existing), False
            now = self._utcnow()
            run = ChatRestRun(
                owner_user_id=owner_user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                request_fingerprint=request_fingerprint,
                status="pending",
                expires_at=now + timedelta(hours=max(1, retention_hours)),
            )
            session.add(run)
            try:
                session.commit()
                session.refresh(run)
                return self._snapshot(run), True
            except IntegrityError:
                session.rollback()
                existing = (
                    session.query(ChatRestRun)
                    .filter(
                        ChatRestRun.owner_user_id == owner_user_id,
                        ChatRestRun.conversation_id == conversation_id,
                        ChatRestRun.request_id == request_id,
                    )
                    .one()
                )
                if str(existing.request_fingerprint) != request_fingerprint:
                    raise ChatRestIdempotencyConflict(
                        "Idempotency key was already used with a different request"
                    )
                return self._snapshot(existing), False
        finally:
            if should_close:
                session.close()

    def claim_pending(
        self,
        *,
        run_id: str,
        producer_token: str,
        lease_seconds: int,
    ) -> bool:
        session, should_close = self._open_session()
        try:
            now = self._utcnow()
            updated = (
                session.query(ChatRestRun)
                .filter(ChatRestRun.id == run_id, ChatRestRun.status == "pending")
                .update(
                    {
                        ChatRestRun.status: "running",
                        ChatRestRun.producer_token: producer_token,
                        ChatRestRun.lease_until: now
                        + timedelta(seconds=max(1, lease_seconds)),
                        ChatRestRun.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(updated or 0) == 1
        finally:
            if should_close:
                session.close()

    def finish(
        self,
        *,
        run_id: str,
        producer_token: str,
        status: str,
        result: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> bool:
        if status not in {"completed", "failed"}:
            raise ValueError("Terminal REST run status required")
        session, should_close = self._open_session()
        try:
            now = self._utcnow()
            updated = (
                session.query(ChatRestRun)
                .filter(
                    ChatRestRun.id == run_id,
                    ChatRestRun.status == "running",
                    ChatRestRun.producer_token == producer_token,
                )
                .update(
                    {
                        ChatRestRun.status: status,
                        ChatRestRun.result_json: result,
                        ChatRestRun.error_code: error_code,
                        ChatRestRun.lease_until: None,
                        ChatRestRun.completed_at: now,
                        ChatRestRun.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(updated or 0) == 1
        finally:
            if should_close:
                session.close()

    def cleanup_expired(self) -> int:
        session, should_close = self._open_session()
        try:
            deleted = (
                session.query(ChatRestRun)
                .filter(
                    ChatRestRun.status.in_({"completed", "failed"}),
                    ChatRestRun.expires_at < self._utcnow(),
                )
                .delete(synchronize_session=False)
            )
            session.commit()
            return int(deleted or 0)
        finally:
            if should_close:
                session.close()
