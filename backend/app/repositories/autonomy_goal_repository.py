from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db import db
from app.models.autonomy_models import AutonomyGoal, AutonomyGoalTransition


TERMINAL_GOAL_STATUSES = {"completed", "failed"}


class AutonomyGoalRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def create_goal(
        self,
        *,
        goal_id: str,
        title: str,
        description: str,
        priority: int = 5,
        success_criteria: str | None = None,
        deadline_ts: float | None = None,
        source: str = "api",
    ) -> AutonomyGoal:
        s = self._get_session()
        try:
            row = AutonomyGoal(
                id=goal_id,
                title=title,
                description=description,
                priority=priority,
                status="pending",
                success_criteria=success_criteria,
                deadline_ts=deadline_ts,
                source=source,
            )
            s.add(row)
            s.flush()
            s.add(
                AutonomyGoalTransition(
                    goal_id=goal_id,
                    from_status=None,
                    to_status="pending",
                    reason="created",
                    actor=source or "api",
                )
            )
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def list_goals(
        self,
        *,
        status: str | None = None,
        include_terminal: bool = False,
        limit: int | None = None,
    ) -> list[AutonomyGoal]:
        s = self._get_session()
        try:
            q = s.query(AutonomyGoal)
            if status:
                q = q.filter(AutonomyGoal.status == status)
            elif not include_terminal:
                q = q.filter(~AutonomyGoal.status.in_(tuple(TERMINAL_GOAL_STATUSES)))
            q = q.order_by(AutonomyGoal.priority.asc(), AutonomyGoal.created_at.asc())
            if isinstance(limit, int) and limit > 0:
                q = q.limit(limit)
            return q.all()
        finally:
            if not self._session:
                s.close()

    def get_goal(self, goal_id: str) -> AutonomyGoal | None:
        s = self._get_session()
        try:
            return s.query(AutonomyGoal).filter(AutonomyGoal.id == goal_id).first()
        finally:
            if not self._session:
                s.close()

    def get_next_pending_goal(self) -> AutonomyGoal | None:
        s = self._get_session()
        try:
            return (
                s.query(AutonomyGoal)
                .filter(AutonomyGoal.status == "pending")
                .order_by(AutonomyGoal.priority.asc(), AutonomyGoal.created_at.asc())
                .first()
            )
        finally:
            if not self._session:
                s.close()

    def transition_status(
        self,
        goal_id: str,
        to_status: str,
        *,
        reason: str | None = None,
        task_id: str | None = None,
        actor: str = "system",
    ) -> AutonomyGoal | None:
        s = self._get_session()
        try:
            row = s.query(AutonomyGoal).filter(AutonomyGoal.id == goal_id).first()
            if row is None:
                return None

            current_status = str(row.status or "").strip().lower()
            next_status = str(to_status or "").strip().lower()
            if not next_status:
                return row

            if current_status == next_status:
                return row

            row.status = next_status
            row.updated_at = datetime.utcnow()
            if next_status in TERMINAL_GOAL_STATUSES:
                row.closed_at = datetime.utcnow()
                row.closed_reason = reason
            else:
                row.closed_at = None
                row.closed_reason = None
            s.add(
                AutonomyGoalTransition(
                    goal_id=goal_id,
                    from_status=current_status or None,
                    to_status=next_status,
                    reason=reason,
                    task_id=task_id,
                    actor=actor or "system",
                )
            )
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def delete_goal(self, goal_id: str) -> bool:
        s = self._get_session()
        try:
            row = s.query(AutonomyGoal).filter(AutonomyGoal.id == goal_id).first()
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True
        finally:
            if not self._session:
                s.close()

    def list_transitions(self, goal_id: str, limit: int = 100) -> list[AutonomyGoalTransition]:
        s = self._get_session()
        try:
            return (
                s.query(AutonomyGoalTransition)
                .filter(AutonomyGoalTransition.goal_id == goal_id)
                .order_by(AutonomyGoalTransition.id.asc())
                .limit(limit)
                .all()
            )
        finally:
            if not self._session:
                s.close()

    @staticmethod
    def decimal_to_float(value: Decimal | float | int | None) -> float | None:
        if value is None:
            return None
        return float(value)
