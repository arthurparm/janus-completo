from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import db
from app.models.autonomy_models import AutonomyLoopLease


class AutonomyLockRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def try_acquire(
        self,
        *,
        scope_key: str,
        owner_id: str,
        ttl_seconds: int,
        metadata_json: str | None = None,
    ) -> tuple[bool, AutonomyLoopLease | None]:
        s = self._get_session()
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=max(1, ttl_seconds))
        try:
            row = s.query(AutonomyLoopLease).filter(AutonomyLoopLease.scope_key == scope_key).first()
            if row is None:
                row = AutonomyLoopLease(
                    scope_key=scope_key,
                    owner_id=owner_id,
                    acquired_at=now,
                    heartbeat_at=now,
                    expires_at=expires_at,
                    metadata_json=metadata_json,
                )
                s.add(row)
                s.commit()
                s.refresh(row)
                return True, row

            if row.owner_id == owner_id or (row.expires_at and row.expires_at <= now):
                row.owner_id = owner_id
                row.acquired_at = now
                row.heartbeat_at = now
                row.expires_at = expires_at
                row.metadata_json = metadata_json
                s.commit()
                s.refresh(row)
                return True, row

            return False, row
        except IntegrityError:
            s.rollback()
            row = s.query(AutonomyLoopLease).filter(AutonomyLoopLease.scope_key == scope_key).first()
            if row and (row.owner_id == owner_id or (row.expires_at and row.expires_at <= now)):
                row.owner_id = owner_id
                row.acquired_at = now
                row.heartbeat_at = now
                row.expires_at = expires_at
                row.metadata_json = metadata_json
                s.commit()
                s.refresh(row)
                return True, row
            return False, row
        finally:
            if not self._session:
                s.close()

    def renew(self, *, scope_key: str, owner_id: str, ttl_seconds: int) -> tuple[bool, AutonomyLoopLease | None]:
        s = self._get_session()
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=max(1, ttl_seconds))
        try:
            row = s.query(AutonomyLoopLease).filter(AutonomyLoopLease.scope_key == scope_key).first()
            if row is None or row.owner_id != owner_id:
                return False, row
            row.heartbeat_at = now
            row.expires_at = expires_at
            s.commit()
            s.refresh(row)
            return True, row
        finally:
            if not self._session:
                s.close()

    def release(self, *, scope_key: str, owner_id: str) -> bool:
        s = self._get_session()
        try:
            row = s.query(AutonomyLoopLease).filter(AutonomyLoopLease.scope_key == scope_key).first()
            if row is None or row.owner_id != owner_id:
                return False
            s.delete(row)
            s.commit()
            return True
        finally:
            if not self._session:
                s.close()

    def get(self, scope_key: str) -> AutonomyLoopLease | None:
        s = self._get_session()
        try:
            return s.query(AutonomyLoopLease).filter(AutonomyLoopLease.scope_key == scope_key).first()
        finally:
            if not self._session:
                s.close()
