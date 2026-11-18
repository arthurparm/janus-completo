from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.config_models import Base


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"
    id = Column(String(36), primary_key=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    conversation_id = Column(String(100), nullable=False)
    message_id = Column(String(100), nullable=True)
    rating = Column(String(20), nullable=False)
    feedback_type = Column(String(20), nullable=False)
    comment = Column(Text, nullable=True)
    context_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    __table_args__ = (
        Index("idx_feedback_owner_created", "owner_user_id", "created_at"),
        Index(
            "idx_feedback_owner_conversation",
            "owner_user_id",
            "conversation_id",
            "created_at",
        ),
    )
