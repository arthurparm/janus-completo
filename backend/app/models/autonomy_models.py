from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
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
    sprint_id = Column(String(100), ForeignKey("autonomy_sprints.id", ondelete="SET NULL"), nullable=True)
    source_kind = Column(String(100), nullable=True)
    source_fingerprint = Column(String(128), nullable=True)
    source_ref = Column(String(500), nullable=True)
    area = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True)
    auto_created = Column(Boolean, default=False)
    llm_provider = Column(String(100), nullable=True)
    llm_model = Column(String(200), nullable=True)
    fallback_used = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    closed_reason = Column(Text, nullable=True)
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
    sprint = relationship("AutonomySprint", back_populates="tasks")
    __table_args__ = (
        Index("idx_autonomy_goal_status_priority", "status", "priority", "created_at"),
        Index("idx_autonomy_goal_source", "source"),
        Index("idx_autonomy_goal_sprint", "sprint_id", "status"),
        Index("idx_autonomy_goal_fingerprint", "source_fingerprint", "status"),
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


class AutonomySprintType(Base):
    __tablename__ = "autonomy_sprint_types"
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True)
    generated_by = Column(String(20), default="janus")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    sprints = relationship("AutonomySprint", back_populates="sprint_type")
    __table_args__ = (
        Index("idx_autonomy_sprint_type_status", "status"),
        Index("idx_autonomy_sprint_type_name", "name"),
    )


class AutonomySprint(Base):
    __tablename__ = "autonomy_sprints"
    id = Column(String(100), primary_key=True)
    sprint_type_id = Column(
        String(100),
        ForeignKey("autonomy_sprint_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(300), nullable=False)
    status = Column(String(20), default="active")
    start_ts = Column(Numeric(18, 6), nullable=True)
    end_ts = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    sprint_type = relationship("AutonomySprintType", back_populates="sprints")
    tasks = relationship("AutonomyGoal", back_populates="sprint")
    __table_args__ = (
        Index("idx_autonomy_sprint_type_status", "sprint_type_id", "status"),
        Index("idx_autonomy_sprint_time", "start_ts", "end_ts"),
    )


class AutonomyTaskEvidence(Base):
    __tablename__ = "autonomy_task_evidence"
    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(String(100), ForeignKey("autonomy_goals.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(100), nullable=False)
    source_uri = Column(String(500), nullable=True)
    payload_json = Column(Text, nullable=True)
    score = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    __table_args__ = (
        Index("idx_autonomy_task_evidence_goal", "goal_id", "created_at"),
        Index("idx_autonomy_task_evidence_type", "evidence_type"),
    )


class AutonomySelfStudyRun(Base):
    __tablename__ = "autonomy_self_study_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger_type = Column(String(50), nullable=False)
    mode = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    base_commit = Column(String(80), nullable=True)
    target_commit = Column(String(80), nullable=True)
    files_total = Column(Integer, default=0)
    files_processed = Column(Integer, default=0)
    status = Column(String(20), default="running")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    finished_at = Column(DateTime, nullable=True)
    files = relationship(
        "AutonomySelfStudyFile",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    __table_args__ = (
        Index("idx_autonomy_self_study_runs_status", "status", "created_at"),
    )


class AutonomySelfStudyFile(Base):
    __tablename__ = "autonomy_self_study_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer,
        ForeignKey("autonomy_self_study_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path = Column(String(1000), nullable=False)
    change_type = Column(String(20), nullable=True)
    sha_before = Column(String(80), nullable=True)
    sha_after = Column(String(80), nullable=True)
    summary_status = Column(String(20), default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    run = relationship("AutonomySelfStudyRun", back_populates="files")
    __table_args__ = (
        Index("idx_autonomy_self_study_files_run", "run_id", "summary_status"),
        Index("idx_autonomy_self_study_files_path", "file_path"),
    )


class AutonomySelfStudyState(Base):
    __tablename__ = "autonomy_self_study_state"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_studied_commit = Column(String(80), nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    __table_args__ = (
        Index("idx_autonomy_self_study_state_updated", "updated_at"),
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
