from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.db import db
from app.models.outbox_models import OutboxEvent


@dataclass(frozen=True)
class OutboxEventRecord:
    id: int
    event_type: str
    payload_json: dict[str, Any]


class OutboxRepositoryError(Exception):
    pass


class OutboxRepository:
    def enqueue(
        self,
        *,
        event_type: str,
        payload_json: dict[str, Any],
        aggregate_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> int:
        session = db.get_session_direct()
        try:
            if dedupe_key:
                existing = (
                    session.query(OutboxEvent)
                    .filter(OutboxEvent.dedupe_key == dedupe_key)
                    .first()
                )
                if existing:
                    return int(existing.id)

            event = OutboxEvent(
                event_type=event_type,
                aggregate_id=aggregate_id,
                dedupe_key=dedupe_key,
                payload_json=payload_json,
                status="pending",
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return int(event.id)
        except IntegrityError:
            session.rollback()
            if dedupe_key:
                existing = (
                    session.query(OutboxEvent)
                    .filter(OutboxEvent.dedupe_key == dedupe_key)
                    .first()
                )
                if existing:
                    return int(existing.id)
            raise OutboxRepositoryError("Falha ao inserir evento no outbox.")
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao inserir evento no outbox: {e}") from e
        finally:
            session.close()

    def claim_pending(self, *, limit: int = 50) -> list[OutboxEventRecord]:
        session = db.get_session_direct()
        now = datetime.utcnow()
        try:
            query = (
                session.query(OutboxEvent)
                .filter(
                    OutboxEvent.status.in_(("pending", "retry")),
                    OutboxEvent.next_attempt_at <= now,
                )
                .order_by(OutboxEvent.created_at.asc())
            )
            try:
                query = query.with_for_update(skip_locked=True)
            except Exception:
                pass

            rows = query.limit(limit).all()
            claimed: list[OutboxEventRecord] = []
            for row in rows:
                row.status = "processing"
                claimed.append(
                    OutboxEventRecord(
                        id=int(row.id),
                        event_type=str(row.event_type),
                        payload_json=dict(row.payload_json or {}),
                    )
                )
            session.commit()
            return claimed
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao reservar eventos pendentes: {e}") from e
        finally:
            session.close()

    def mark_sent(self, event_id: int) -> None:
        session = db.get_session_direct()
        try:
            row = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if not row:
                return
            row.status = "sent"
            row.last_error = None
            session.commit()
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao marcar evento como enviado: {e}") from e
        finally:
            session.close()

    def mark_retry(
        self,
        event_id: int,
        *,
        error: str,
        max_attempts: int = 10,
    ) -> str:
        session = db.get_session_direct()
        try:
            row = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if not row:
                return "missing"

            attempts = int(row.attempts or 0) + 1
            row.attempts = attempts
            row.last_error = error[:4000]

            if attempts >= max_attempts:
                row.status = "dead"
            else:
                backoff_seconds = min(300, 2 ** min(attempts, 8))
                row.status = "retry"
                row.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)

            session.commit()
            return str(row.status)
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao marcar evento para retry: {e}") from e
        finally:
            session.close()

    def get_stats(self) -> dict[str, int]:
        session = db.get_session_direct()
        try:
            rows = session.query(OutboxEvent.status).all()
            stats = {"pending": 0, "retry": 0, "processing": 0, "sent": 0, "dead": 0}
            for (status,) in rows:
                key = str(status or "pending")
                if key not in stats:
                    stats[key] = 0
                stats[key] += 1
            return stats
        finally:
            session.close()

    def requeue_dead(self, *, limit: int = 100) -> int:
        session = db.get_session_direct()
        try:
            rows = (
                session.query(OutboxEvent)
                .filter(OutboxEvent.status == "dead")
                .order_by(OutboxEvent.updated_at.asc())
                .limit(limit)
                .all()
            )
            count = 0
            for row in rows:
                row.status = "retry"
                row.next_attempt_at = datetime.utcnow()
                count += 1
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao reencaminhar eventos mortos: {e}") from e
        finally:
            session.close()
