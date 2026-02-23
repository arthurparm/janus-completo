import asyncio
import json
from typing import Any

import structlog

from app.repositories.observability_repository import ObservabilityRepository

logger = structlog.get_logger(__name__)


class ChatEventDbLogger:
    def __init__(self, repo: ObservabilityRepository):
        self._repo = repo

    async def log_event(self, payload: dict[str, Any]) -> None:
        event = {
            "user_id": payload.get("user_id"),
            "endpoint": f"chat_event:{payload.get('conversation_id')}",
            "action": payload.get("event_type"),
            "tool": payload.get("agent_role"),
            "status": "published",
            "latency_ms": None,
            "trace_id": payload.get("trace_id"),
            "details_json": json.dumps(payload, ensure_ascii=False),
        }
        try:
            await asyncio.to_thread(self._repo.record_audit_event, event)
        except Exception as e:
            logger.error("chat_event_db_log_failed", error=str(e))
