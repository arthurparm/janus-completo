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


class AutonomyGoal(Base):
    __tablename__ = "autonomy_goals"
    id = Column(String(100), primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Integer, default=5)
    status = Column(String(20), default="pending")
    success_criteria = Column(Text, nullable=True)
    deadline_ts = Column(Numeric(18, 6), nullable=True)
    source = Column(String(50), default="api")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    transitions = relationship(
        "AutonomyGoalTransition",
        back_populates="goal",
        cascade="all, delete-orphan",
    )
    __table_args__ = (
        Index("idx_autonomy_goal_status_priority", "status", "priority", "created_at"),
        Index("idx_autonomy_goal_source", "source"),
    )


class AutonomyGoalTransition(Base):
    __tablename__ = "autonomy_goal_transitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(String(100), ForeignKey("autonomy_goals.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    task_id = Column(String(100), nullable=True)
    actor = Column(String(50), default="system")
    created_at = Column(DateTime, default=func.current_timestamp())
    goal = relationship("AutonomyGoal", back_populates="transitions")
    __table_args__ = (
        Index("idx_autonomy_goal_transition_goal", "goal_id", "created_at"),
        Index("idx_autonomy_goal_transition_actor", "actor"),
    )


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


class AutonomyEnqueueLedger(Base):
    __tablename__ = "autonomy_enqueue_ledger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("autonomy_runs.id", ondelete="SET NULL"), nullable=True)
    goal_id = Column(String(100), nullable=False)
    task_id = Column(String(100), nullable=True)
    cycle = Column(Integer, default=0)
    selected_tool = Column(String(100), nullable=True)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    publish_status = Column(String(20), default="pending")
    publish_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    __table_args__ = (
        Index("idx_autonomy_enqueue_goal_cycle", "goal_id", "cycle"),
        Index("idx_autonomy_enqueue_task_id", "task_id"),
    )


class AutonomyLoopLease(Base):
    __tablename__ = "autonomy_loop_leases"
    scope_key = Column(String(200), primary_key=True)
    owner_id = Column(String(200), nullable=False)
    acquired_at = Column(DateTime, default=func.current_timestamp())
    heartbeat_at = Column(DateTime, default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    metadata_json = Column(Text, nullable=True)
    __table_args__ = (
        Index("idx_autonomy_lease_expires_at", "expires_at"),
        Index("idx_autonomy_lease_owner", "owner_id"),
    )
