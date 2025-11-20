from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.config_models import Base

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=func.current_timestamp())
    arms = relationship("ExperimentArm", back_populates="experiment", cascade="all, delete-orphan")
    __table_args__ = (
        Index("idx_experiment_user_status", "user_id", "status"),
        # Evita nomes duplicados por usuário (ou global quando user_id é NULL)
        UniqueConstraint("name", "user_id", name="unique_experiment_name_user"),
    )

class ExperimentArm(Base):
    __tablename__ = "experiment_arms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    model_spec = Column(String(200), nullable=False)
    experiment = relationship("Experiment", back_populates="arms")

class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    arm_id = Column(Integer, ForeignKey("experiment_arms.id", ondelete="CASCADE"), nullable=False)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Numeric(12, 6), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

class ExperimentFeedback(Base):
    __tablename__ = "experiment_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    arm_id = Column(Integer, ForeignKey("experiment_arms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(100), nullable=False)
    rating = Column(Numeric(4, 2), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
