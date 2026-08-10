import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
)

from app.models.config_models import Base


class ChatRestRun(Base):  # type: ignore[misc]
    __tablename__ = "chat_rest_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(String(128), nullable=False)
    conversation_id = Column(String(128), nullable=False)
    request_id = Column(String(128), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    producer_token = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    result_json = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "conversation_id",
            "request_id",
            name="uq_chat_rest_owner_conversation_request",
        ),
        Index("idx_chat_rest_status_lease", "status", "lease_until"),
        Index("idx_chat_rest_owner_created", "owner_user_id", "created_at"),
    )
