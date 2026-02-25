import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

import structlog
from fastapi import Request

from app.config import settings
from app.repositories.autonomy_goal_repository import AutonomyGoalRepository
from app.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


class GoalStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Goal:
    id: str
    title: str
    description: str
    priority: int = 5  # 1 alta, 10 baixa
    status: str = GoalStatus.PENDING
    success_criteria: str | None = None
    deadline_ts: float | None = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class GoalManager:
    """Gerenciador de metas (fonte principal em SQL; Firestore opcional para espelho)."""

    def __init__(
        self,
        memory_service: MemoryService | None,
        goal_repo: AutonomyGoalRepository | None = None,
    ):
        self._memory_service = memory_service
        self._goal_repo = goal_repo or AutonomyGoalRepository()
        self._firestore_enabled = getattr(settings, "FIREBASE_ENABLED", False)
        self._collection = "goals"
        logger.info("GoalManager initialized with SQL storage (Firestore optional mirror).")

    def _to_goal(self, row) -> Goal | None:
        if row is None:
            return None
        created_at = getattr(row, "created_at", None)
        updated_at = getattr(row, "updated_at", None)
        deadline_ts = AutonomyGoalRepository.decimal_to_float(getattr(row, "deadline_ts", None))
        return Goal(
            id=str(row.id),
            title=str(row.title),
            description=str(row.description),
            priority=int(getattr(row, "priority", 5) or 5),
            status=str(getattr(row, "status", GoalStatus.PENDING) or GoalStatus.PENDING),
            success_criteria=getattr(row, "success_criteria", None),
            deadline_ts=deadline_ts,
            created_at=created_at.timestamp() if isinstance(created_at, datetime) else time.time(),
            updated_at=updated_at.timestamp() if isinstance(updated_at, datetime) else time.time(),
        )

    def _save_to_firestore(self, goal: Goal):
        """Sync goal to Firestore if habilitado."""
        if not self._firestore_enabled:
            return
        try:
            from google.cloud import firestore

            db = firestore.Client()
            doc_ref = db.collection(self._collection).document(goal.id)
            doc_ref.set(goal.to_dict())
            logger.debug("goal_firestore_synced", goal_id=goal.id)
        except Exception as e:
            logger.warning("goal_firestore_sync_failed", goal_id=goal.id, error=str(e))

    def _delete_from_firestore(self, goal_id: str):
        if not self._firestore_enabled:
            return
        try:
            from google.cloud import firestore

            db = firestore.Client()
            doc_ref = db.collection(self._collection).document(goal_id)
            doc_ref.delete()
            logger.debug("goal_firestore_deleted", goal_id=goal_id)
        except Exception as e:
            logger.warning("goal_firestore_delete_failed", goal_id=goal_id, error=str(e))

    def _log_to_memory_service(self, goal: Goal, action: str):
        if not self._memory_service:
            return
        try:
            event_text = f"Goal {action}: {goal.title} (Priority: {goal.priority}, Status: {goal.status})"
            logger.info("goal_event_logged", goal_id=goal.id, action=action, summary=event_text)
        except Exception as e:
            logger.warning("goal_memory_log_failed", goal_id=goal.id, error=str(e))

    def create_goal(
        self,
        title: str,
        description: str,
        priority: int = 5,
        success_criteria: str | None = None,
        deadline_ts: float | None = None,
    ) -> Goal:
        goal_id = uuid.uuid4().hex
        goal = Goal(
            id=goal_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            success_criteria=success_criteria,
            deadline_ts=deadline_ts,
        )
        row = self._goal_repo.create_goal(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            priority=goal.priority,
            success_criteria=goal.success_criteria,
            deadline_ts=goal.deadline_ts,
            source="api",
        )
        goal = self._to_goal(row) or goal
        self._save_to_firestore(goal)
        self._log_to_memory_service(goal, "created")
        return goal

    def list_goals(self, status: str | None = None) -> list[Goal]:
        rows = self._goal_repo.list_goals(status=status, include_terminal=False)
        return [g for g in (self._to_goal(r) for r in rows) if g is not None]

    def update_goal_status(
        self,
        goal_id: str,
        status: str,
        *,
        reason: str | None = None,
        task_id: str | None = None,
        actor: str = "api",
    ) -> Goal | None:
        row = self._goal_repo.transition_status(
            goal_id,
            status,
            reason=reason,
            task_id=task_id,
            actor=actor,
        )
        goal = self._to_goal(row)
        if not goal:
            return None
        if status in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
            logger.info("goal_terminal_state_set", goal_id=goal_id, status=status)
        self._save_to_firestore(goal)
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._to_goal(self._goal_repo.get_goal(goal_id))

    def get_next_goal(self) -> Goal | None:
        return self._to_goal(self._goal_repo.get_next_pending_goal())

    def delete_goal(self, goal_id: str) -> bool:
        removed = self.get_goal(goal_id)
        ok = self._goal_repo.delete_goal(goal_id)
        if ok:
            self._delete_from_firestore(goal_id)
            if removed:
                self._log_to_memory_service(removed, "deleted")
        return ok


def get_goal_manager(request: Request) -> "GoalManager":
    return request.app.state.goal_manager
