from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.config_models import Base


class AutonomyRun(Base):
    __tablename__ = "autonomy_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=True)
    project_id = Column(String(100), nullable=True)
    risk_profile = Column(String(20), default="balanced")
    auto_confirm = Column(String(5), default="True")
    allowlist = Column(Text, nullable=True)
    blocklist = Column(Text, nullable=True)
    max_actions_per_cycle = Column(Integer, default=20)
    max_seconds_per_cycle = Column(Integer, default=60)
    interval_seconds = Column(Integer, default=60)
    status = Column(String(20), default="running")
    cycles = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.current_timestamp())
    stopped_at = Column(DateTime, nullable=True)
    steps = relationship("AutonomyStep", back_populates="run", cascade="all, delete-orphan")
    __table_args__ = (Index("idx_autonomy_run_user", "user_id", "project_id", "status"),)


class AutonomyStep(Base):
    __tablename__ = "autonomy_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("autonomy_runs.id", ondelete="CASCADE"), nullable=False)
    cycle = Column(Integer, default=0)
    tool = Column(String(100), nullable=False)
    input_preview = Column(Text, nullable=True)
    input_length = Column(Integer, default=0)
    result_preview = Column(Text, nullable=True)
    result_length = Column(Integer, default=0)
    success = Column(Integer, default=1)
    error = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(10, 4), default=0)
    created_at = Column(DateTime, default=func.current_timestamp())
    run = relationship("AutonomyRun", back_populates="steps")
    __table_args__ = (Index("idx_autonomy_step_run_cycle", "run_id", "cycle"),)
