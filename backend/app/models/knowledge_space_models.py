from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.models.config_models import Base


class KnowledgeSpace(Base):
    __tablename__ = "knowledge_spaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_space_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(64), nullable=False, default="documentation")
    source_id = Column(String(255), nullable=True)
    edition_or_version = Column(String(128), nullable=True)
    language = Column(String(32), nullable=True)
    parent_collection_id = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    consolidation_status = Column(String(32), nullable=False, default="not_started")
    consolidation_summary = Column(Text, nullable=True)
    last_consolidated_at = Column(DateTime, nullable=True)
    sections_total = Column(Integer, nullable=False, default=0)
    sections_indexed = Column(Integer, nullable=False, default=0)
    sections_skipped_as_noise = Column(Integer, nullable=False, default=0)
    canonical_frames_total = Column(Integer, nullable=False, default=0)
    consolidation_quality_score = Column(String(32), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_knowledge_spaces_user", "user_id"),
        Index("idx_knowledge_spaces_user_status", "user_id", "consolidation_status"),
    )
