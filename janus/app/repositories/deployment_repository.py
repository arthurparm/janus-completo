from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.db.mysql_config import mysql_db
from app.models.config_models import Base


class ModelDeployment(Base):
    __tablename__ = "model_deployments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(200), nullable=False)
    status = Column(String(20), default="staged")
    rollout_percent = Column(Integer, default=0)
    precheck_passed = Column(Integer, default=0)
    bias_score = Column(Integer, default=0)
    safety_warnings = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    __table_args__ = (UniqueConstraint("model_id", name="unique_model_deployment"),)


class DeploymentRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def stage(self, model_id: str, percent: int) -> dict[str, Any]:
        s = self._get_session()
        try:
            item = s.query(ModelDeployment).filter(ModelDeployment.model_id == model_id).first()
            if item is None:
                item = ModelDeployment(
                    model_id=model_id, rollout_percent=int(percent), status="staged"
                )
                s.add(item)
            else:
                item.rollout_percent = int(percent)
                item.status = "staged"
            s.commit()
            s.refresh(item)
            return {
                "model_id": item.model_id,
                "status": item.status,
                "rollout_percent": item.rollout_percent,
            }
        finally:
            if not self._session:
                s.close()

    def publish(self, model_id: str) -> dict[str, Any]:
        s = self._get_session()
        try:
            item = s.query(ModelDeployment).filter(ModelDeployment.model_id == model_id).first()
            if item is None:
                item = ModelDeployment(model_id=model_id, rollout_percent=100, status="active")
                s.add(item)
            else:
                item.rollout_percent = 100
                item.status = "active"
            s.commit()
            s.refresh(item)
            return {
                "model_id": item.model_id,
                "status": item.status,
                "rollout_percent": item.rollout_percent,
            }
        finally:
            if not self._session:
                s.close()

    def rollback(self, model_id: str) -> dict[str, Any]:
        s = self._get_session()
        try:
            item = s.query(ModelDeployment).filter(ModelDeployment.model_id == model_id).first()
            if item is None:
                return {"model_id": model_id, "status": "none"}
            item.status = "rolled_back"
            item.rollout_percent = 0
            s.commit()
            s.refresh(item)
            return {
                "model_id": item.model_id,
                "status": item.status,
                "rollout_percent": item.rollout_percent,
            }
        finally:
            if not self._session:
                s.close()
