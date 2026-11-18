import random
from typing import cast

from app.db import db
from app.models.ab_assignment_models import ExperimentAssignment
from app.models.ab_experiment_models import Experiment, ExperimentArm, ExperimentResult
from sqlalchemy.orm import Session


class ABExperimentRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def create_experiment(self, name: str, owner_user_id: int) -> Experiment:
        s = self._get_session()
        try:
            exp = Experiment(
                name=name, owner_user_id=owner_user_id, user_id=str(owner_user_id)
            )
            s.add(exp)
            s.commit()
            s.refresh(exp)
            return exp
        finally:
            if not self._session:
                s.close()

    def get_owned_experiment(self, experiment_id: int, owner_user_id: int) -> Experiment | None:
        s = self._get_session()
        try:
            return (
                s.query(Experiment)
                .filter(
                    Experiment.id == experiment_id,
                    Experiment.owner_user_id == owner_user_id,
                )
                .first()
            )
        finally:
            if not self._session:
                s.close()

    def add_arm(
        self, experiment_id: int, owner_user_id: int, name: str, model_spec: str
    ) -> ExperimentArm | None:
        s = self._get_session()
        try:
            owned = (
                s.query(Experiment.id)
                .filter(
                    Experiment.id == experiment_id,
                    Experiment.owner_user_id == owner_user_id,
                )
                .first()
            )
            if owned is None:
                return None
            arm = ExperimentArm(experiment_id=experiment_id, name=name, model_spec=model_spec)
            s.add(arm)
            s.commit()
            s.refresh(arm)
            return arm
        finally:
            if not self._session:
                s.close()

    def list_experiments(self, owner_user_id: int, limit: int = 50) -> list[Experiment]:
        s = self._get_session()
        try:
            q = s.query(Experiment).filter(Experiment.owner_user_id == owner_user_id)
            return cast(
                list[Experiment], q.order_by(Experiment.created_at.desc()).limit(limit).all()
            )
        finally:
            if not self._session:
                s.close()

    def add_result(
        self,
        experiment_id: int,
        arm_id: int,
        metric_name: str,
        metric_value: float,
        *,
        owner_user_id: int | None,
    ) -> ExperimentResult | None:
        s = self._get_session()
        try:
            query = s.query(ExperimentArm).join(
                Experiment, Experiment.id == ExperimentArm.experiment_id
            ).filter(
                ExperimentArm.id == arm_id,
                ExperimentArm.experiment_id == experiment_id,
            )
            if owner_user_id is not None:
                query = query.filter(Experiment.owner_user_id == owner_user_id)
            if query.first() is None:
                return None
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
