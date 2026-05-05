from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Task(BaseModel):
    id: str
    description: str
    assigned_to: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = []
    context: Optional[Dict] = None

class Plan(BaseModel):
    goal: str
    tasks: List[Task]
    metadata: Dict = {}
