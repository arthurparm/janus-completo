from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from app.core.governance.data_classification import (
    DataClassification,
    classify_text,
    default_retention_decision,
)
from app.repositories.data_governance_repository import DataGovernanceRepository

logger = structlog.get_logger(__name__)


class DataGovernanceServiceError(Exception):
    pass


class DataGovernanceService:
    def __init__(self, repo: DataGovernanceRepository | None = None):
        self._repo = repo or DataGovernanceRepository()

    @staticmethod
    def _compute_retention_until(retention_days: int | None) -> datetime | None:
        if retention_days is None:
            return None
        return datetime.now(timezone.utc) + timedelta(days=max(0, int(retention_days)))

    def register_auto(
        self,
        *,
        user_id: int | None,
        resource_type: str,
        resource_id: str,
        sample_text: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        classification = classify_text(sample_text)
        decision = default_retention_decision(classification)
        retention_until = self._compute_retention_until(decision.retention_days)
        return self._repo.upsert_record(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            classification=decision.classification,
            classification_source="auto",
            retention_policy=decision.retention_policy,
            retention_days=decision.retention_days,
            retention_until=retention_until,
            metadata_json=metadata,
        )

    def register_manual(
        self,
        *,
        user_id: int | None,
        resource_type: str,
        resource_id: str,
        classification: str,
        retention_policy: str,
        retention_days: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        normalized = str(classification or "").strip().upper()
        if normalized not in {DataClassification.PII, DataClassification.SECRET, DataClassification.INTERNAL}:
            raise DataGovernanceServiceError("Classificação inválida.")
        normalized_policy = str(retention_policy or "").strip().lower()
        if normalized_policy not in {"persistent", "days"}:
            raise DataGovernanceServiceError("Retention policy inválida.")
        retention_until = None
        if normalized_policy == "days":
            if retention_days is None:
                raise DataGovernanceServiceError("retention_days é obrigatório para policy=days.")
            retention_until = self._compute_retention_until(retention_days)

        return self._repo.upsert_record(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            classification=normalized,
            classification_source="manual",
            retention_policy=normalized_policy,
            retention_days=retention_days,
            retention_until=retention_until,
            metadata_json=metadata,
        )


data_governance_service = DataGovernanceService()

