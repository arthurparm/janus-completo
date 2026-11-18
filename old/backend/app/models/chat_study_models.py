import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.models.config_models import Base


class ChatStudyRun(Base):  # type: ignore[misc]
    __tablename__ = "chat_study_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(128), nullable=False)
    conversation_id = Column(String(128), nullable=False)
    message_id = Column(String(128), nullable=False)
    question = Column(Text, nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)
    worker_token = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    placeholder_message = Column(Text, nullable=True)
    failure_classification = Column(String(64), nullable=True)
    final_response_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "conversation_id",
            "message_id",
            name="uq_chat_study_owner_conversation_message",
        ),
        Index("idx_chat_study_status_lease", "status", "lease_until"),
    )
