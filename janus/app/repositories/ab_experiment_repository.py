from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.mysql_config import mysql_db
from app.models.ab_experiment_models import Experiment, ExperimentArm, ExperimentResult

class ABExperimentRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def create_experiment(self, name: str, user_id: Optional[str]) -> Experiment:
        s = self._get_session()
        try:
            exp = Experiment(name=name, user_id=user_id)
            s.add(exp)
            s.commit()
            s.refresh(exp)
            return exp
        finally:
            if not self._session:
                s.close()

    def add_arm(self, experiment_id: int, name: str, model_spec: str) -> ExperimentArm:
        s = self._get_session()
        try:
            arm = ExperimentArm(experiment_id=experiment_id, name=name, model_spec=model_spec)
            s.add(arm)
            s.commit()
            s.refresh(arm)
            return arm
        finally:
            if not self._session:
                s.close()

    def list_experiments(self, user_id: Optional[str], limit: int = 50) -> List[Experiment]:
        s = self._get_session()
        try:
            q = s.query(Experiment)
            if user_id:
                q = q.filter(Experiment.user_id == user_id)
            return q.order_by(Experiment.created_at.desc()).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def add_result(self, experiment_id: int, arm_id: int, metric_name: str, metric_value: float) -> ExperimentResult:
        s = self._get_session()
        try:
            res = ExperimentResult(experiment_id=experiment_id, arm_id=arm_id, metric_name=metric_name, metric_value=metric_value)
            s.add(res)
            s.commit()
            s.refresh(res)
            return res
        finally:
            if not self._session:
                s.close()