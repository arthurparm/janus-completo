import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import structlog

from app.services.memory_service import MemoryService
from fastapi import Request

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
    success_criteria: Optional[str] = None
    deadline_ts: Optional[float] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())


class GoalManager:
    """Gerenciador simples de metas com armazenamento em memória e persistência básica em Memória Episódica."""

    def __init__(self, memory_service: MemoryService):
        self._memory_service = memory_service
        self._goals: Dict[str, Goal] = {}

    def create_goal(self, title: str, description: str, priority: int = 5,
                    success_criteria: Optional[str] = None, deadline_ts: Optional[float] = None) -> Goal:
        goal_id = uuid.uuid4().hex
        goal = Goal(id=goal_id, title=title.strip(), description=description.strip(), priority=priority,
                    success_criteria=success_criteria, deadline_ts=deadline_ts)
        self._goals[goal_id] = goal
        try:
            # Persistência básica no repositório de memória
            asyncio_run = getattr(self._memory_service, "add_experience", None)
            if callable(asyncio_run):
                # MemoryService.add_experience é assíncrono; usar create_task se disponível no contexto
                try:
                    import asyncio
                    asyncio.create_task(self._memory_service.add_experience(
                        type="goal",
                        content=f"{goal.title}\n{goal.description}",
                        metadata={"goal_id": goal_id, "priority": priority, "status": goal.status}
                    ))
                except Exception:
                    # Fallback: ignore se não houver loop
                    pass
        except Exception as e:
            logger.warning("Falha ao persistir meta na memória", exc_info=e)
        return goal

    def list_goals(self, status: Optional[str] = None) -> List[Goal]:
        items = list(self._goals.values())
        if status:
            items = [g for g in items if g.status == status]
        return sorted(items, key=lambda g: (g.priority, g.created_at))

    def update_goal_status(self, goal_id: str, status: str) -> Optional[Goal]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        goal.status = status
        goal.updated_at = time.time()
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def get_next_goal(self) -> Optional[Goal]:
        pending = self.list_goals(status=GoalStatus.PENDING)
        return pending[0] if pending else None

    def delete_goal(self, goal_id: str) -> bool:
        removed = self._goals.pop(goal_id, None)
        if removed:
            try:
                import asyncio
                asyncio.create_task(self._memory_service.add_experience(
                    type="goal_deleted",
                    content=f"{removed.title}\n{removed.description}",
                    metadata={"goal_id": goal_id, "status": removed.status}
                ))
            except Exception:
                pass
            return True
        return False


# --- Dependency Injection Helper ---
def get_goal_manager(request: Request) -> "GoalManager":
    return request.app.state.goal_manager