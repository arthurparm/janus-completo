from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.db import db
from app.models.outbox_models import OutboxEvent
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError


@dataclass(frozen=True)
class OutboxEventRecord:
    id: int
    message_id: str
    event_type: str
    payload_json: dict[str, Any]
    claim_token: str


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
                message_id=uuid.uuid4().hex,
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

    def claim_pending(
        self,
        *,
        limit: int = 50,
        worker_id: str = "outbox-dispatcher",
        lease_seconds: int = 300,
    ) -> list[OutboxEventRecord]:
        session = db.get_session_direct()
        now = datetime.utcnow()
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        try:
            query = (
                session.query(OutboxEvent)
                .filter(
                    or_(
                        and_(
                            OutboxEvent.status.in_(("pending", "retry")),
                            OutboxEvent.next_attempt_at <= now,
                        ),
                        and_(
                            OutboxEvent.status == "processing",
                            OutboxEvent.lease_until.isnot(None),
                            OutboxEvent.lease_until <= now,
                        ),
                    )
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
                claim_token = uuid.uuid4().hex
                row.status = "processing"
                row.claimed_by = str(worker_id)[:128]
                row.claim_token = claim_token
                row.claimed_at = now
                row.lease_until = lease_until
                claimed.append(
                    OutboxEventRecord(
                        id=int(row.id),
                        message_id=str(row.message_id),
                        event_type=str(row.event_type),
                        payload_json=dict(row.payload_json or {}),
                        claim_token=claim_token,
                    )
                )
            session.commit()
            return claimed
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao reservar eventos pendentes: {e}") from e
        finally:
            session.close()

    def mark_sent(self, event_id: int, *, claim_token: str) -> bool:
        session = db.get_session_direct()
        try:
            row = (
                session.query(OutboxEvent)
                .filter(
                    OutboxEvent.id == event_id,
                    OutboxEvent.status == "processing",
                    OutboxEvent.claim_token == claim_token,
                )
                .first()
            )
            if not row:
                return False
            row.status = "sent"
            row.last_error = None
            row.claimed_by = None
            row.claim_token = None
            row.claimed_at = None
            row.lease_until = None
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao marcar evento como enviado: {e}") from e
        finally:
            session.close()

    def mark_retry(
        self,
        event_id: int,
        *,
        claim_token: str,
        error: str,
        max_attempts: int = 10,
    ) -> str:
        session = db.get_session_direct()
        try:
            row = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if not row:
                return "missing"
            if row.status != "processing" or row.claim_token != claim_token:
                return "stale"

            attempts = int(row.attempts or 0) + 1
            row.attempts = attempts
            row.last_error = error[:4000]
            row.claimed_by = None
            row.claim_token = None
            row.claimed_at = None
            row.lease_until = None

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
                row.claimed_by = None
                row.claim_token = None
                row.claimed_at = None
                row.lease_until = None
                count += 1
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise OutboxRepositoryError(f"Falha ao reencaminhar eventos mortos: {e}") from e
        finally:
            session.close()
