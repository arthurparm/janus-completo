from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.db import db
from app.models.chat_stream_models import ChatStreamEvent, ChatStreamRun
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ChatStreamRepositoryError(RuntimeError):
    pass


class ChatStreamIdempotencyConflict(ChatStreamRepositoryError):
    pass


class ChatStreamClaimLost(ChatStreamRepositoryError):
    pass


@dataclass(frozen=True)
class ChatStreamRunState:
    id: str
    owner_user_id: int
    session_id: int
    request_id: str
    request_fingerprint: str
    status: str
    last_event_sequence: int
    lease_until: datetime | None
    error_code: str | None

    @property
    def terminal(self) -> bool:
        return self.status in {"completed", "failed"}


@dataclass(frozen=True)
class ChatStreamEventState:
    sequence: int
    payload: str


class ChatStreamRepository:
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
    def _snapshot(run: ChatStreamRun) -> ChatStreamRunState:
        return ChatStreamRunState(
            id=str(run.id),
            owner_user_id=int(run.owner_user_id),
            session_id=int(run.session_id),
            request_id=str(run.request_id),
            request_fingerprint=str(run.request_fingerprint),
            status=str(run.status),
            last_event_sequence=int(run.last_event_sequence or 0),
            lease_until=run.lease_until,
            error_code=str(run.error_code) if run.error_code else None,
        )

    @staticmethod
    def _validate_fingerprint(run: ChatStreamRun, request_fingerprint: str) -> None:
        if str(run.request_fingerprint) != str(request_fingerprint):
            raise ChatStreamIdempotencyConflict(
                "Idempotency key was already used with a different request"
            )

    def begin_or_get(
        self,
        *,
        owner_user_id: int,
        session_id: int | str,
        request_id: str,
        request_fingerprint: str,
        retention_hours: int,
    ) -> tuple[ChatStreamRunState, bool]:
        try:
            resolved_session_id = int(str(session_id))
        except (TypeError, ValueError) as exc:
            raise ChatStreamRepositoryError("Invalid chat session identifier") from exc
        session, should_close = self._open_session()
        try:
            existing = (
                session.query(ChatStreamRun)
                .filter(
                    ChatStreamRun.owner_user_id == owner_user_id,
                    ChatStreamRun.session_id == resolved_session_id,
                    ChatStreamRun.request_id == request_id,
                )
                .first()
            )
            if existing is not None:
                self._validate_fingerprint(existing, request_fingerprint)
                return self._snapshot(existing), False

            now = datetime.utcnow()
            run = ChatStreamRun(
                owner_user_id=owner_user_id,
                session_id=resolved_session_id,
                request_id=request_id,
                request_fingerprint=request_fingerprint,
                status="pending",
                last_event_sequence=0,
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
                    session.query(ChatStreamRun)
                    .filter(
                        ChatStreamRun.owner_user_id == owner_user_id,
                        ChatStreamRun.session_id == resolved_session_id,
                        ChatStreamRun.request_id == request_id,
                    )
                    .one()
                )
                self._validate_fingerprint(existing, request_fingerprint)
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
            now = datetime.utcnow()
            updated = (
                session.query(ChatStreamRun)
                .filter(ChatStreamRun.id == run_id, ChatStreamRun.status == "pending")
                .update(
                    {
                        ChatStreamRun.status: "running",
                        ChatStreamRun.producer_token: producer_token,
                        ChatStreamRun.lease_until: now
                        + timedelta(seconds=max(1, lease_seconds)),
                        ChatStreamRun.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(updated or 0) == 1
        finally:
            if should_close:
                session.close()

    def renew_lease(
        self,
        *,
        run_id: str,
        producer_token: str,
        lease_seconds: int,
    ) -> bool:
        session, should_close = self._open_session()
        try:
            now = datetime.utcnow()
            updated = (
                session.query(ChatStreamRun)
                .filter(
                    ChatStreamRun.id == run_id,
                    ChatStreamRun.status == "running",
                    ChatStreamRun.producer_token == producer_token,
                )
                .update(
                    {
                        ChatStreamRun.lease_until: now
                        + timedelta(seconds=max(1, lease_seconds)),
                        ChatStreamRun.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(updated or 0) == 1
        finally:
            if should_close:
                session.close()

    def append_event(
        self,
        *,
        run_id: str,
        producer_token: str,
        payload: str,
        lease_seconds: int,
    ) -> ChatStreamEventState:
        session, should_close = self._open_session()
        try:
            run = (
                session.query(ChatStreamRun)
                .filter(ChatStreamRun.id == run_id)
                .with_for_update()
                .one_or_none()
            )
            if (
                run is None
                or run.status != "running"
                or run.producer_token != producer_token
            ):
                raise ChatStreamClaimLost("Chat stream producer no longer owns the run")
            sequence = int(run.last_event_sequence or 0) + 1
            now = datetime.utcnow()
            event = ChatStreamEvent(run_id=run_id, sequence=sequence, payload=payload)
            session.add(event)
            run.last_event_sequence = sequence
            run.updated_at = now
            run.lease_until = now + timedelta(seconds=max(1, lease_seconds))
            session.commit()
            return ChatStreamEventState(sequence=sequence, payload=payload)
        finally:
            if should_close:
                session.close()

    def finish(
        self,
        *,
        run_id: str,
        producer_token: str,
        status: str,
        error_code: str | None = None,
    ) -> bool:
        if status not in {"completed", "failed"}:
            raise ValueError("Terminal chat stream status required")
        session, should_close = self._open_session()
        try:
            now = datetime.utcnow()
            updated = (
                session.query(ChatStreamRun)
                .filter(
                    ChatStreamRun.id == run_id,
                    ChatStreamRun.status == "running",
                    ChatStreamRun.producer_token == producer_token,
                )
                .update(
                    {
                        ChatStreamRun.status: status,
                        ChatStreamRun.error_code: error_code,
                        ChatStreamRun.completed_at: now,
                        ChatStreamRun.updated_at: now,
                        ChatStreamRun.lease_until: None,
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(updated or 0) == 1
        finally:
            if should_close:
                session.close()

    def interrupt_stale_run(
        self,
        *,
        run_id: str,
        owner_user_id: int,
        error_payload: str,
        error_code: str,
    ) -> bool:
        session, should_close = self._open_session()
        try:
            now = datetime.utcnow()
            run = (
                session.query(ChatStreamRun)
                .filter(
                    ChatStreamRun.id == run_id,
                    ChatStreamRun.owner_user_id == owner_user_id,
                )
                .with_for_update()
                .one_or_none()
            )
            if (
                run is None
                or run.status != "running"
                or run.lease_until is None
                or run.lease_until >= now
            ):
                return False
            sequence = int(run.last_event_sequence or 0) + 1
            session.add(
                ChatStreamEvent(
                    run_id=run_id,
                    sequence=sequence,
                    payload=error_payload,
                )
            )
            run.last_event_sequence = sequence
            run.status = "failed"
            run.error_code = error_code
            run.completed_at = now
            run.updated_at = now
            run.lease_until = None
            session.commit()
            return True
        finally:
            if should_close:
                session.close()

    def get_run(self, *, run_id: str, owner_user_id: int) -> ChatStreamRunState | None:
        session, should_close = self._open_session()
        try:
            run = (
                session.query(ChatStreamRun)
                .filter(
                    ChatStreamRun.id == run_id,
                    ChatStreamRun.owner_user_id == owner_user_id,
                )
                .one_or_none()
            )
            return self._snapshot(run) if run is not None else None
        finally:
            if should_close:
                session.close()

    def list_events(
        self,
        *,
        run_id: str,
        owner_user_id: int,
        after_sequence: int,
        limit: int = 200,
    ) -> list[ChatStreamEventState]:
        session, should_close = self._open_session()
        try:
            owned_run = (
                session.query(ChatStreamRun.id)
                .filter(
                    ChatStreamRun.id == run_id,
                    ChatStreamRun.owner_user_id == owner_user_id,
                )
                .one_or_none()
            )
            if owned_run is None:
                return []
            rows = (
                session.query(ChatStreamEvent)
                .filter(
                    ChatStreamEvent.run_id == run_id,
                    ChatStreamEvent.sequence > max(0, after_sequence),
                )
                .order_by(ChatStreamEvent.sequence.asc())
                .limit(max(1, min(limit, 1000)))
                .all()
            )
            return [
                ChatStreamEventState(sequence=int(row.sequence), payload=str(row.payload))
                for row in rows
            ]
        finally:
            if should_close:
                session.close()
