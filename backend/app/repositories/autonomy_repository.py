from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import db
from app.models.autonomy_models import AutonomyEnqueueLedger, AutonomyRun, AutonomyStep


class AutonomyRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def create_run(
        self,
        user_id: str | None,
        project_id: str | None,
        risk_profile: str,
        auto_confirm: bool,
        allowlist: list[str],
        blocklist: list[str],
        max_actions_per_cycle: int,
        max_seconds_per_cycle: int,
        interval_seconds: int,
    ) -> AutonomyRun:
        s = self._get_session()
        try:
            run = AutonomyRun(
                user_id=user_id,
                project_id=project_id,
                risk_profile=risk_profile,
                auto_confirm=str(bool(auto_confirm)),
                allowlist=",".join(allowlist or []),
                blocklist=",".join(blocklist or []),
                max_actions_per_cycle=max_actions_per_cycle,
                max_seconds_per_cycle=max_seconds_per_cycle,
                interval_seconds=interval_seconds,
                status="running",
                cycles=0,
            )
            s.add(run)
            s.commit()
            s.refresh(run)
            return run
        finally:
            if not self._session:
                s.close()

    def increment_cycles(self, run_id: int) -> None:
        s = self._get_session()
        try:
            run = s.query(AutonomyRun).filter(AutonomyRun.id == run_id).first()
            if run:
                run.cycles = int(run.cycles or 0) + 1
                s.commit()
        finally:
            if not self._session:
                s.close()

    def stop_run(self, run_id: int) -> None:
        s = self._get_session()
        try:
            run = s.query(AutonomyRun).filter(AutonomyRun.id == run_id).first()
            if run:
                run.status = "stopped"
                from datetime import datetime

                run.stopped_at = datetime.utcnow()
                s.commit()
        finally:
            if not self._session:
                s.close()

    def add_step(
        self,
        run_id: int,
        cycle: int,
        tool: str,
        input_preview: str | None,
        input_length: int,
        result_preview: str | None,
        result_length: int,
        success: bool,
        error: str | None,
        duration_seconds: float,
    ) -> AutonomyStep:
        s = self._get_session()
        try:
            step = AutonomyStep(
                run_id=run_id,
                cycle=cycle,
                tool=tool,
                input_preview=input_preview,
                input_length=input_length,
                result_preview=result_preview,
                result_length=result_length,
                success=1 if success else 0,
                error=error,
                duration_seconds=duration_seconds,
            )
            s.add(step)
            s.commit()
            s.refresh(step)
            return step
        finally:
            if not self._session:
                s.close()

    def get_active_run(
        self, user_id: str | None = None, project_id: str | None = None
    ) -> AutonomyRun | None:
        """Recupera a run ativa mais recente (status='running') para permitir restauração após reinício."""
        s = self._get_session()
        try:
            q = s.query(AutonomyRun).filter(AutonomyRun.status == "running")
            if user_id:
                q = q.filter(AutonomyRun.user_id == user_id)
            if project_id:
                q = q.filter(AutonomyRun.project_id == project_id)
            return q.order_by(desc(AutonomyRun.started_at)).first()
        finally:
            if not self._session:
                s.close()

    def list_runs(
        self, user_id: str | None, project_id: str | None, limit: int = 50
    ) -> list[AutonomyRun]:
        s = self._get_session()
        try:
            q = s.query(AutonomyRun)
            if user_id:
                q = q.filter(AutonomyRun.user_id == user_id)
            if project_id:
                q = q.filter(AutonomyRun.project_id == project_id)
            return q.order_by(desc(AutonomyRun.started_at)).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def get_run(self, run_id: int) -> AutonomyRun | None:
        s = self._get_session()
        try:
            return s.query(AutonomyRun).filter(AutonomyRun.id == run_id).first()
        finally:
            if not self._session:
                s.close()

    def list_steps(
        self, run_id: int, cycle: int | None = None, limit: int = 100
    ) -> list[AutonomyStep]:
        s = self._get_session()
        try:
            q = s.query(AutonomyStep).filter(AutonomyStep.run_id == run_id)
            if cycle is not None:
                q = q.filter(AutonomyStep.cycle == cycle)
            return q.order_by(AutonomyStep.id.asc()).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def create_or_get_enqueue_ledger(
        self,
        *,
        run_id: int | None,
        goal_id: str,
        cycle: int,
        selected_tool: str | None,
        idempotency_key: str,
    ) -> AutonomyEnqueueLedger:
        s = self._get_session()
        try:
            existing = (
                s.query(AutonomyEnqueueLedger)
                .filter(AutonomyEnqueueLedger.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return existing

            row = AutonomyEnqueueLedger(
                run_id=run_id,
                goal_id=goal_id,
                cycle=cycle,
                selected_tool=selected_tool,
                idempotency_key=idempotency_key,
                publish_status="pending",
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        except IntegrityError:
            s.rollback()
            existing = (
                s.query(AutonomyEnqueueLedger)
                .filter(AutonomyEnqueueLedger.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return existing
            raise
        finally:
            if not self._session:
                s.close()

    def mark_enqueue_published(self, ledger_id: int, task_id: str) -> AutonomyEnqueueLedger | None:
        s = self._get_session()
        try:
            row = (
                s.query(AutonomyEnqueueLedger).filter(AutonomyEnqueueLedger.id == ledger_id).first()
            )
            if not row:
                return None
            row.task_id = task_id
            row.publish_status = "published"
            row.publish_error = None
            row.updated_at = datetime.utcnow()
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def mark_enqueue_failed(self, ledger_id: int, error: str) -> AutonomyEnqueueLedger | None:
        s = self._get_session()
        try:
            row = (
                s.query(AutonomyEnqueueLedger).filter(AutonomyEnqueueLedger.id == ledger_id).first()
            )
            if not row:
                return None
            row.publish_status = "failed"
            row.publish_error = error
            row.updated_at = datetime.utcnow()
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def find_latest_enqueue_by_goal(self, goal_id: str) -> AutonomyEnqueueLedger | None:
        s = self._get_session()
        try:
            return (
                s.query(AutonomyEnqueueLedger)
                .filter(AutonomyEnqueueLedger.goal_id == goal_id)
                .order_by(desc(AutonomyEnqueueLedger.id))
                .first()
            )
        finally:
            if not self._session:
                s.close()

    def list_enqueues(self, run_id: int, limit: int = 100) -> list[AutonomyEnqueueLedger]:
        s = self._get_session()
        try:
            q = s.query(AutonomyEnqueueLedger).filter(AutonomyEnqueueLedger.run_id == run_id)
            return q.order_by(AutonomyEnqueueLedger.id.asc()).limit(limit).all()
        finally:
            if not self._session:
                s.close()
