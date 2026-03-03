from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.models.config_models import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    args_json = Column(Text, nullable=False)
    run_id = Column(Integer, ForeignKey("autonomy_runs.id", ondelete="SET NULL"), nullable=True)
    cycle = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")
    simulation_summary_json = Column(Text, nullable=True)
    simulation_generated_at = Column(DateTime, nullable=True)
    simulation_version = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    decided_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("idx_pending_actions_user_status", "user_id", "status"),)
