from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.models.config_models import Base


class DocumentManifest(Base):
    __tablename__ = "document_manifests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(128), nullable=False)
    conversation_id = Column(String(128), nullable=True)
    knowledge_space_id = Column(String(255), nullable=True)
    source_type = Column(String(64), nullable=True)
    source_id = Column(String(255), nullable=True)
    edition_or_version = Column(String(128), nullable=True)
    language = Column(String(32), nullable=True)
    parent_collection_id = Column(String(255), nullable=True)
    file_name = Column(String(512), nullable=False)
    content_type = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="queued")
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    chunks_total = Column(Integer, nullable=False, default=0)
    chunks_indexed = Column(Integer, nullable=False, default=0)
    semantic_doc_type = Column(String(64), nullable=True)
    semantic_summary = Column(Text, nullable=True)
    semantic_confidence = Column(String(32), nullable=True)
    storage_path = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_document_manifests_user_status", "user_id", "status"),
        Index("idx_document_manifests_user_conversation", "user_id", "conversation_id"),
        Index("idx_document_manifests_space", "user_id", "knowledge_space_id"),
    )
