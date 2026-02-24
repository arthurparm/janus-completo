import time
import uuid
from dataclasses import asdict, dataclass, field

import structlog
from fastapi import Request

from app.config import settings
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
    """Gerenciador de metas apenas em memória (Firestore opcional)."""

    def __init__(self, memory_service: MemoryService):
        self._memory_service = memory_service
        self._goals: dict[str, Goal] = {}
        self._firestore_enabled = getattr(settings, "FIREBASE_ENABLED", False)
        self._collection = "goals"
        logger.info("GoalManager initialized with in-memory storage only (Firestore optional).")

    def _save_to_firestore(self, goal: Goal):
        """Sync goal to Firestore if habilitado."""
        if not self._firestore_enabled:
            return
        try:
            from google.cloud import firestore

            db = firestore.Client()
            doc_ref = db.collection(self._collection).document(goal.id)
            doc_ref.set(goal.to_dict())
            logger.debug("log_debug", message=f"Goal {goal.id} synced to Firestore")
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to sync goal {goal.id} to Firestore: {e}")

    def _delete_from_firestore(self, goal_id: str):
        if not self._firestore_enabled:
            return
        try:
            from google.cloud import firestore

            db = firestore.Client()
            doc_ref = db.collection(self._collection).document(goal_id)
            doc_ref.delete()
            logger.debug("log_debug", message=f"Goal {goal_id} deleted from Firestore")
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to delete goal {goal_id} from Firestore: {e}")

    def _log_to_memory_service(self, goal: Goal, action: str):
        if not self._memory_service:
            return
        try:
            event_text = f"Goal {action}: {goal.title} (Priority: {goal.priority}, Status: {goal.status})"
            logger.info("log_info", message=f"Goal event: {event_text}", goal_id=goal.id, action=action)
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to log goal {goal.id} to memory service: {e}")

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
        self._goals[goal_id] = goal
        self._save_to_firestore(goal)
        self._log_to_memory_service(goal, "created")
        return goal

    def list_goals(self, status: str | None = None) -> list[Goal]:
        items = list(self._goals.values())
        if status:
            items = [g for g in items if g.status == status]
        return sorted(items, key=lambda g: (g.priority, g.created_at))

    def update_goal_status(self, goal_id: str, status: str) -> Goal | None:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        goal.status = status
        goal.updated_at = time.time()
        if status in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
            self._goals.pop(goal_id, None)
            logger.info("log_info", message=f"Goal {goal_id} archived (terminal state).")
        else:
            self._goals[goal_id] = goal
        self._save_to_firestore(goal)
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def get_next_goal(self) -> Goal | None:
        pending = [g for g in self._goals.values() if g.status == GoalStatus.PENDING]
        sorted_pending = sorted(pending, key=lambda g: (g.priority, g.created_at))
        return sorted_pending[0] if sorted_pending else None

    def delete_goal(self, goal_id: str) -> bool:
        removed = self._goals.pop(goal_id, None)
        self._delete_from_firestore(goal_id)
        if removed:
            self._log_to_memory_service(removed, "deleted")
        return True


def get_goal_manager(request: Request) -> "GoalManager":
    return request.app.state.goal_manager
