from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.mysql_config import mysql_db
from app.models.autonomy_models import AutonomyRun, AutonomyStep

class AutonomyRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def create_run(self,
                   user_id: Optional[str],
                   project_id: Optional[str],
                   risk_profile: str,
                   auto_confirm: bool,
                   allowlist: List[str],
                   blocklist: List[str],
                   max_actions_per_cycle: int,
                   max_seconds_per_cycle: int,
                   interval_seconds: int) -> AutonomyRun:
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

    def add_step(self, run_id: int, cycle: int, tool: str,
                 input_preview: Optional[str], input_length: int,
                 result_preview: Optional[str], result_length: int,
                 success: bool, error: Optional[str], duration_seconds: float) -> AutonomyStep:
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

    def list_runs(self, user_id: Optional[str], project_id: Optional[str], limit: int = 50) -> List[AutonomyRun]:
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

    def get_run(self, run_id: int) -> Optional[AutonomyRun]:
        s = self._get_session()
        try:
            return s.query(AutonomyRun).filter(AutonomyRun.id == run_id).first()
        finally:
            if not self._session:
                s.close()

    def list_steps(self, run_id: int, cycle: Optional[int] = None, limit: int = 100) -> List[AutonomyStep]:
        s = self._get_session()
        try:
            q = s.query(AutonomyStep).filter(AutonomyStep.run_id == run_id)
            if cycle is not None:
                q = q.filter(AutonomyStep.cycle == cycle)
            return q.order_by(AutonomyStep.id.asc()).limit(limit).all()
        finally:
            if not self._session:
                s.close()