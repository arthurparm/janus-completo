from __future__ import annotations

from typing import Any

import structlog

from app.services.procedural_memory_service import procedural_memory_service
from app.services.secret_memory_service import secret_memory_service
from app.services.user_preference_memory_service import user_preference_memory_service

logger = structlog.get_logger(__name__)


class ActiveMemoryService:
    """Separates memory capture from memory recall and promotes only durable signals."""

    async def maybe_capture_from_message(
        self,
        *,
        message: str,
        conversation_id: str | None,
        identity_source: str = "unknown",
        target_entity: str | None = None,
    ) -> dict[str, Any] | None:
        if not str(message or "").strip():
            return None

        try:
            secret_result = await secret_memory_service.maybe_capture_from_message(
                message=message,
                conversation_id=conversation_id,
            )
            if secret_result:
                return {"memory_class": "secret", **secret_result}
        except Exception as exc:
            logger.warning("active_memory_secret_capture_failed", error=str(exc))

        try:
            procedural_result = await procedural_memory_service.maybe_capture_from_message(
                message=message,
                conversation_id=conversation_id,
            )
            if procedural_result:
                return {"memory_class": "procedural", **procedural_result}
        except Exception as exc:
            logger.warning("active_memory_procedural_capture_failed", error=str(exc))

        try:
            preference_result = await user_preference_memory_service.maybe_capture_from_message(
                message=message,
                conversation_id=conversation_id,
            )
            if preference_result:
                return {"memory_class": "semantic", **preference_result}
        except Exception as exc:
            logger.warning("active_memory_preference_capture_failed", error=str(exc))

        return None


active_memory_service = ActiveMemoryService()
