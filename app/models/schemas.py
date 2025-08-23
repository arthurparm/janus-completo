# app/models/schemas.py
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

class Experience(BaseModel):
    """
    Representa uma única experiência ou evento a ser memorizado.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: str  # Ex: "action_success", "action_failure", "observation"
    content: str
    metadata: dict = Field(default_factory=dict)