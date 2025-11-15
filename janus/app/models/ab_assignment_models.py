from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.models.config_models import Base

class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(100), nullable=False)
    arm_id = Column(Integer, ForeignKey("experiment_arms.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="unique_experiment_user_assignment"),
    )