from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, func

from app.models.config_models import Base


class ProductivityTask(Base):  # type: ignore[misc]
    __tablename__ = "productivity_tasks"

    task_id = Column(String(64), primary_key=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    operation = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="queued")
    provider_resource_id = Column(String(255), nullable=True)
    error_code = Column(String(128), nullable=True)
    error_message = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "operation IN ('google_calendar_add_event', 'google_mail_send')",
            name="ck_productivity_tasks_operation",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_productivity_tasks_status",
        ),
        Index("idx_productivity_tasks_owner_created", "owner_user_id", "created_at"),
        Index("idx_productivity_tasks_status_updated", "status", "updated_at"),
    )
