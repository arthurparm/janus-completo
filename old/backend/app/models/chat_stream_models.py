import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.models.config_models import Base


class ChatStreamRun(Base):  # type: ignore[misc]
    __tablename__ = "chat_stream_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id = Column(String(128), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    producer_token = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    last_event_sequence = Column(Integer, nullable=False, default=0)
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
            "session_id",
            "request_id",
            name="uq_chat_stream_owner_session_request",
        ),
        Index("idx_chat_stream_run_status_lease", "status", "lease_until"),
        Index("idx_chat_stream_run_owner_created", "owner_user_id", "created_at"),
    )


class ChatStreamEvent(Base):  # type: ignore[misc]
    __tablename__ = "chat_stream_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(36),
        ForeignKey("chat_stream_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence = Column(Integer, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_chat_stream_event_sequence"),
        Index("idx_chat_stream_event_cursor", "run_id", "sequence"),
    )
