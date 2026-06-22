from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.config_models import Base


class DataGovernanceRecord(Base):
    __tablename__ = "data_governance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(255), nullable=False)

    classification = Column(String(16), nullable=False)
    classification_source = Column(String(16), nullable=False)

    retention_policy = Column(String(32), nullable=False)
    retention_days = Column(Integer, nullable=True)
    retention_until = Column(DateTime, nullable=True)

    metadata_json = Column(JSONB, nullable=True)

    purge_job_id = Column(String(64), nullable=True)
    purged_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index("idx_data_gov_resource", "resource_type", "resource_id"),
        Index("idx_data_gov_user", "user_id", "resource_type"),
        Index("idx_data_gov_retention", "retention_until", "purged_at"),
    )

