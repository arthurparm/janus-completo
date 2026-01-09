import random

from sqlalchemy.orm import Session

from app.db.mysql_config import mysql_db
from app.models.ab_assignment_models import ExperimentAssignment
from app.models.ab_experiment_models import Experiment, ExperimentArm, ExperimentResult


class ABExperimentRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def create_experiment(self, name: str, user_id: str | None) -> Experiment:
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

    def list_experiments(self, user_id: str | None, limit: int = 50) -> list[Experiment]:
        s = self._get_session()
        try:
            q = s.query(Experiment)
            if user_id:
                q = q.filter(Experiment.user_id == user_id)
            return q.order_by(Experiment.created_at.desc()).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def add_result(
        self, experiment_id: int, arm_id: int, metric_name: str, metric_value: float
    ) -> ExperimentResult:
        s = self._get_session()
        try:
            res = ExperimentResult(
                experiment_id=experiment_id,
                arm_id=arm_id,
                metric_name=metric_name,
                metric_value=metric_value,
            )
            s.add(res)
            s.commit()
            s.refresh(res)
            return res
        finally:
            if not self._session:
                s.close()

    def assign_user(self, experiment_id: int, user_id: str) -> ExperimentAssignment:
        s = self._get_session()
        try:
            existing = (
                s.query(ExperimentAssignment)
                .filter(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.user_id == user_id,
                )
                .first()
            )
            if existing:
                return existing
            arms = s.query(ExperimentArm).filter(ExperimentArm.experiment_id == experiment_id).all()
            if not arms:
                raise ValueError("No arms for experiment")
            arm = random.choice(arms)
            asg = ExperimentAssignment(experiment_id=experiment_id, user_id=user_id, arm_id=arm.id)
            s.add(asg)
            s.commit()
            s.refresh(asg)
            return asg
        finally:
            if not self._session:
                s.close()

    def get_assignment(self, experiment_id: int, user_id: str) -> ExperimentAssignment | None:
        s = self._get_session()
        try:
            return (
                s.query(ExperimentAssignment)
                .filter(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.user_id == user_id,
                )
                .first()
            )
        finally:
            if not self._session:
                s.close()
