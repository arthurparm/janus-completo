from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db import db
from app.models.autonomy_models import (
    AutonomyGoal,
    AutonomyGoalTransition,
    AutonomySelfStudyFile,
    AutonomySelfStudyRun,
    AutonomySelfStudyState,
    AutonomySprint,
    AutonomySprintType,
    AutonomyTaskEvidence,
)


TERMINAL_STATUSES = {"completed", "failed"}


class AutonomyAdminRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    @staticmethod
    def _to_float(value: Decimal | float | int | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def get_or_create_sprint_type(self, *, name: str, generated_by: str = "janus") -> AutonomySprintType:
        slug = name.strip().lower().replace(" ", "-")[:180]
        s = self._get_session()
        try:
            row = s.query(AutonomySprintType).filter(AutonomySprintType.slug == slug).first()
            if row:
                return row
            row = AutonomySprintType(
                id=uuid.uuid4().hex,
                name=name.strip()[:200],
                slug=slug,
                generated_by=generated_by,
                status="active",
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def get_or_create_active_sprint(
        self,
        *,
        sprint_type_id: str,
        sprint_name: str,
        start_ts: float | None = None,
        end_ts: float | None = None,
    ) -> AutonomySprint:
        s = self._get_session()
        try:
            row = (
                s.query(AutonomySprint)
                .filter(
                    and_(
                        AutonomySprint.sprint_type_id == sprint_type_id,
                        AutonomySprint.status == "active",
                    )
                )
                .order_by(AutonomySprint.created_at.desc())
                .first()
            )
            if row:
                return row
            row = AutonomySprint(
                id=uuid.uuid4().hex,
                sprint_type_id=sprint_type_id,
                name=sprint_name[:300],
                status="active",
                start_ts=start_ts,
                end_ts=end_ts,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def create_task(
        self,
        *,
        title: str,
        description: str,
        sprint_id: str | None,
        priority: int,
        source: str,
        source_kind: str,
        source_fingerprint: str,
        source_ref: str | None = None,
        area: str | None = None,
        severity: str | None = None,
        auto_created: bool = False,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        fallback_used: bool = False,
    ) -> AutonomyGoal:
        s = self._get_session()
        try:
            row = AutonomyGoal(
                id=uuid.uuid4().hex,
                title=title[:500],
                description=description,
                priority=max(1, min(10, int(priority))),
                status="pending",
                source=source,
                sprint_id=sprint_id,
                source_kind=source_kind,
                source_fingerprint=source_fingerprint,
                source_ref=source_ref,
                area=area,
                severity=severity,
                auto_created=bool(auto_created),
                llm_provider=llm_provider,
                llm_model=llm_model,
                fallback_used=bool(fallback_used),
            )
            s.add(row)
            s.flush()
            s.add(
                AutonomyGoalTransition(
                    goal_id=row.id,
                    from_status=None,
                    to_status="pending",
                    reason="created_by_backlog_sync",
                    actor="autonomy_admin",
                )
            )
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def add_task_evidence(
        self,
        *,
        goal_id: str,
        evidence_type: str,
        source_uri: str | None,
        payload: dict[str, Any] | None,
        score: float | None = None,
    ) -> AutonomyTaskEvidence:
        s = self._get_session()
        try:
            row = AutonomyTaskEvidence(
                goal_id=goal_id,
                evidence_type=evidence_type,
                source_uri=source_uri,
                payload_json=json.dumps(payload or {}, ensure_ascii=False),
                score=score,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def find_open_task_by_fingerprint(self, source_fingerprint: str) -> AutonomyGoal | None:
        s = self._get_session()
        try:
            return (
                s.query(AutonomyGoal)
                .filter(
                    and_(
                        AutonomyGoal.source_fingerprint == source_fingerprint,
                        ~AutonomyGoal.status.in_(tuple(TERMINAL_STATUSES)),
                    )
                )
                .order_by(AutonomyGoal.updated_at.desc())
                .first()
            )
        finally:
            if not self._session:
                s.close()

    def count_auto_created_today(self) -> int:
        s = self._get_session()
        try:
            return int(
                s.query(func.count(AutonomyGoal.id))
                .filter(
                    and_(
                        AutonomyGoal.auto_created.is_(True),
                        func.date(AutonomyGoal.created_at) == func.current_date(),
                    )
                )
                .scalar()
                or 0
            )
        finally:
            if not self._session:
                s.close()

    def list_board(self, *, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        s = self._get_session()
        try:
            query = (
                s.query(AutonomyGoal, AutonomySprint, AutonomySprintType)
                .outerjoin(AutonomySprint, AutonomyGoal.sprint_id == AutonomySprint.id)
                .outerjoin(AutonomySprintType, AutonomySprint.sprint_type_id == AutonomySprintType.id)
            )
            if status:
                query = query.filter(AutonomyGoal.status == status)
            rows = (
                query.order_by(AutonomyGoal.priority.asc(), AutonomyGoal.created_at.desc())
                .limit(limit)
                .all()
            )

            grouped: dict[str, dict[str, Any]] = {}
            for goal, sprint, sprint_type in rows:
                st_id = sprint_type.id if sprint_type else "unassigned"
                if st_id not in grouped:
                    grouped[st_id] = {
                        "sprint_type": {
                            "id": st_id,
                            "name": sprint_type.name if sprint_type else "Sem tipo",
                            "slug": sprint_type.slug if sprint_type else "unassigned",
                        },
                        "sprints": {},
                    }
                sp_id = sprint.id if sprint else "backlog"
                sprint_bucket = grouped[st_id]["sprints"].setdefault(
                    sp_id,
                    {
                        "id": sp_id,
                        "name": sprint.name if sprint else "Backlog",
                        "status": sprint.status if sprint else "active",
                        "start_ts": self._to_float(sprint.start_ts) if sprint else None,
                        "end_ts": self._to_float(sprint.end_ts) if sprint else None,
                        "tasks": [],
                    },
                )
                sprint_bucket["tasks"].append(
                    {
                        "id": goal.id,
                        "title": goal.title,
                        "description": goal.description,
                        "status": goal.status,
                        "priority": goal.priority,
                        "source_kind": goal.source_kind,
                        "source_fingerprint": goal.source_fingerprint,
                        "area": goal.area,
                        "severity": goal.severity,
                        "auto_created": bool(goal.auto_created),
                        "created_at": goal.created_at.isoformat() if goal.created_at else None,
                        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
                    }
                )

            response: list[dict[str, Any]] = []
            for bucket in grouped.values():
                response.append(
                    {
                        "sprint_type": bucket["sprint_type"],
                        "sprints": list(bucket["sprints"].values()),
                    }
                )
            return response
        finally:
            if not self._session:
                s.close()

    def list_open_tasks(self, *, source_kind: str | None = None) -> list[AutonomyGoal]:
        s = self._get_session()
        try:
            q = s.query(AutonomyGoal).filter(~AutonomyGoal.status.in_(tuple(TERMINAL_STATUSES)))
            if source_kind:
                q = q.filter(AutonomyGoal.source_kind == source_kind)
            return q.order_by(AutonomyGoal.updated_at.desc()).all()
        finally:
            if not self._session:
                s.close()

    def close_task(self, goal_id: str, reason: str, actor: str = "autonomy_admin") -> AutonomyGoal | None:
        s = self._get_session()
        try:
            row = s.query(AutonomyGoal).filter(AutonomyGoal.id == goal_id).first()
            if not row:
                return None
            if str(row.status).lower() in TERMINAL_STATUSES:
                return row
            old_status = row.status
            row.status = "completed"
            row.closed_reason = reason
            row.closed_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            s.add(
                AutonomyGoalTransition(
                    goal_id=row.id,
                    from_status=old_status,
                    to_status="completed",
                    reason=reason,
                    actor=actor,
                )
            )
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def create_self_study_run(
        self,
        *,
        trigger_type: str,
        mode: str,
        reason: str | None,
        base_commit: str | None,
        target_commit: str | None,
    ) -> AutonomySelfStudyRun:
        s = self._get_session()
        try:
            run = AutonomySelfStudyRun(
                trigger_type=trigger_type,
                mode=mode,
                reason=reason,
                base_commit=base_commit,
                target_commit=target_commit,
                status="running",
            )
            s.add(run)
            s.commit()
            s.refresh(run)
            return run
        finally:
            if not self._session:
                s.close()

    def add_self_study_file(
        self,
        *,
        run_id: int,
        file_path: str,
        change_type: str | None,
        sha_before: str | None,
        sha_after: str | None,
        summary_status: str = "pending",
        error: str | None = None,
    ) -> AutonomySelfStudyFile:
        s = self._get_session()
        try:
            row = AutonomySelfStudyFile(
                run_id=run_id,
                file_path=file_path,
                change_type=change_type,
                sha_before=sha_before,
                sha_after=sha_after,
                summary_status=summary_status,
                error=error,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row
        finally:
            if not self._session:
                s.close()

    def update_self_study_file_status(self, file_id: int, status: str, error: str | None = None) -> None:
        s = self._get_session()
        try:
            row = s.query(AutonomySelfStudyFile).filter(AutonomySelfStudyFile.id == file_id).first()
            if not row:
                return
            row.summary_status = status
            row.error = error
            s.commit()
        finally:
            if not self._session:
                s.close()

    def finish_self_study_run(
        self,
        run_id: int,
        *,
        files_total: int,
        files_processed: int,
        status: str,
        error: str | None = None,
    ) -> None:
        s = self._get_session()
        try:
            run = s.query(AutonomySelfStudyRun).filter(AutonomySelfStudyRun.id == run_id).first()
            if not run:
                return
            run.files_total = int(files_total)
            run.files_processed = int(files_processed)
            run.status = status
            run.error = error
            run.finished_at = datetime.now(timezone.utc)
            s.commit()
        finally:
            if not self._session:
                s.close()

    def get_self_study_state(self) -> AutonomySelfStudyState:
        s = self._get_session()
        try:
            state = (
                s.query(AutonomySelfStudyState)
                .order_by(AutonomySelfStudyState.id.asc())
                .first()
            )
            if state:
                return state
            state = AutonomySelfStudyState(
                last_studied_commit=None,
                last_success_at=None,
            )
            s.add(state)
            s.commit()
            s.refresh(state)
            return state
        finally:
            if not self._session:
                s.close()

    def update_self_study_state(
        self, *, last_studied_commit: str | None, mark_success: bool = True
    ) -> AutonomySelfStudyState:
        s = self._get_session()
        try:
            state = (
                s.query(AutonomySelfStudyState)
                .order_by(AutonomySelfStudyState.id.asc())
                .first()
            )
            if not state:
                state = AutonomySelfStudyState()
                s.add(state)
                s.flush()
            state.last_studied_commit = last_studied_commit
            if mark_success:
                state.last_success_at = datetime.now(timezone.utc)
            state.updated_at = datetime.now(timezone.utc)
            s.commit()
            s.refresh(state)
            return state
        finally:
            if not self._session:
                s.close()

    def get_latest_running_self_study(self) -> AutonomySelfStudyRun | None:
        s = self._get_session()
        try:
            return (
                s.query(AutonomySelfStudyRun)
                .filter(AutonomySelfStudyRun.status == "running")
                .order_by(AutonomySelfStudyRun.created_at.desc())
                .first()
            )
        finally:
            if not self._session:
                s.close()

    def list_self_study_runs(self, limit: int = 20) -> list[AutonomySelfStudyRun]:
        s = self._get_session()
        try:
            return (
                s.query(AutonomySelfStudyRun)
                .order_by(AutonomySelfStudyRun.created_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            if not self._session:
                s.close()

    def list_self_study_files(self, run_id: int, limit: int = 500) -> list[AutonomySelfStudyFile]:
        s = self._get_session()
        try:
            return (
                s.query(AutonomySelfStudyFile)
                .filter(AutonomySelfStudyFile.run_id == run_id)
                .order_by(AutonomySelfStudyFile.id.asc())
                .limit(limit)
                .all()
            )
        finally:
            if not self._session:
                s.close()
