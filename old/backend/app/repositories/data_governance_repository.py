from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.db import db
from app.models.data_governance_models import DataGovernanceRecord

logger = structlog.get_logger(__name__)


class DataGovernanceRepositoryError(Exception):
    pass


class DataGovernanceRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        return self._session or db.get_session_direct()

    def upsert_record(
        self,
        *,
        user_id: int | None,
        resource_type: str,
        resource_id: str,
        classification: str,
        classification_source: str,
        retention_policy: str,
        retention_days: int | None,
        retention_until: datetime | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> int:
        s = self._get_session()
        try:
            q = s.query(DataGovernanceRecord).filter(
                DataGovernanceRecord.resource_type == str(resource_type),
                DataGovernanceRecord.resource_id == str(resource_id),
            )
            if user_id is not None:
                q = q.filter(DataGovernanceRecord.user_id == int(user_id))
            row = q.first()
            if row is None:
                row = DataGovernanceRecord(
                    user_id=user_id,
                    resource_type=str(resource_type),
                    resource_id=str(resource_id),
                    classification=str(classification),
                    classification_source=str(classification_source),
                    retention_policy=str(retention_policy),
                    retention_days=retention_days,
                    retention_until=retention_until,
                    metadata_json=metadata_json or {},
                )
                s.add(row)
            else:
                row.classification = str(classification)
                row.classification_source = str(classification_source)
                row.retention_policy = str(retention_policy)
                row.retention_days = retention_days
                row.retention_until = retention_until
                if metadata_json:
                    current = row.metadata_json or {}
                    current.update(metadata_json)
                    row.metadata_json = current
            s.commit()
            s.refresh(row)
            return int(row.id)
        except Exception as exc:
            try:
                s.rollback()
            except Exception:
                pass
            logger.warning("data_governance_upsert_failed", error=str(exc))
            raise DataGovernanceRepositoryError("Falha ao persistir metadados de governança.") from exc
        finally:
            if self._session is None:
                s.close()

    def list_expired(self, *, now: datetime | None = None, limit: int = 250) -> list[DataGovernanceRecord]:
        s = self._get_session()
        try:
            cutoff = now or datetime.now(timezone.utc)
            q = (
                s.query(DataGovernanceRecord)
                .filter(DataGovernanceRecord.retention_until.isnot(None))
                .filter(DataGovernanceRecord.retention_until <= cutoff)
                .filter(DataGovernanceRecord.purged_at.is_(None))
                .order_by(DataGovernanceRecord.retention_until.asc())
                .limit(int(limit))
            )
            return list(q.all())
        finally:
            if self._session is None:
                s.close()

    def mark_purged(self, *, record_id: int, purge_job_id: str, purged_at: datetime | None = None) -> None:
        s = self._get_session()
        try:
            row = s.query(DataGovernanceRecord).filter(DataGovernanceRecord.id == int(record_id)).first()
            if row is None:
                return
            row.purge_job_id = str(purge_job_id)
            row.purged_at = purged_at or datetime.now(timezone.utc)
            s.commit()
        except Exception as exc:
            try:
                s.rollback()
            except Exception:
                pass
            logger.warning("data_governance_mark_purged_failed", error=str(exc))
            raise DataGovernanceRepositoryError("Falha ao marcar expurgo.") from exc
        finally:
            if self._session is None:
                s.close()

