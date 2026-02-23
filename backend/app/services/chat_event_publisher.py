"""
Chat Event Publisher Service.
Publishes agent events to RabbitMQ with fallback strategies.
"""

import time
import structlog
from typing import Any
from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.fallback_chain import FallbackChain

logger = structlog.get_logger(__name__)


class ChatEventPublisher:
    """
    Publishes agent events with hierarchical fallbacks.

    Fallback chain:
    1. Primary: RabbitMQ publish
    2. Secondary: Store in database (if available)
    3. Minimal: Log to file
    """

    def __init__(self, db_logger: Any | None = None):
        """
        Initialize event publisher.

        Args:
            db_logger: Optional database logger for fallback
        """
        self.db_logger = db_logger

    async def publish_event(
        self,
        conversation_id: str,
        event_type: str,
        agent_role: str,
        content: str,
        task_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Publish agent event with fallback strategies.

        Args:
            conversation_id: Conversation ID
            event_type: Type of event (e.g., "agent_thought", "tool_call")
            agent_role: Role of agent
            content: Event content
            task_id: Optional task ID
        """
        payload = {
            "conversation_id": conversation_id,
            "event_type": event_type,
            "agent_role": agent_role,
            "content": content,
            "timestamp": time.time(),
            "task_id": task_id or conversation_id,
            "user_id": user_id,
        }

        # Create fallback chain
        chain = FallbackChain(
            strategies=[
                lambda: self._publish_to_rabbitmq(conversation_id, event_type, payload),
                lambda: self._publish_to_database(payload),
                lambda: self._publish_to_log(payload),
            ],
            component_name="event_publish",
        )

        try:
            await chain.execute()
        except Exception as e:
            # All fallbacks failed - log critical error but don't break execution
            logger.error(
                "all_event_publishing_failed",
                conversation_id=conversation_id,
                event_type=event_type,
                error=str(e),
            )

    async def _publish_to_rabbitmq(
        self, conversation_id: str, event_type: str, payload: dict
    ) -> None:
        """Primary strategy: Publish to RabbitMQ."""
        broker = await get_broker()
        routing_key = f"janus.event.conversation.{conversation_id}.{event_type}"

        await broker.publish_to_exchange(
            exchange_name="janus.events",
            routing_key=routing_key,
            message=payload,
        )

        logger.debug(
            "event_published_to_rabbitmq",
            conversation_id=conversation_id,
            event_type=event_type,
        )

    async def _publish_to_database(self, payload: dict) -> None:
        """Secondary strategy: Store in database."""
        if not self.db_logger:
            raise ValueError("Database logger not available")

        await self.db_logger.log_event(payload)

        logger.info(
            "event_published_to_database",
            conversation_id=payload["conversation_id"],
            event_type=payload["event_type"],
        )

    async def _publish_to_log(self, payload: dict) -> None:
        """Minimal fallback: Log to file."""
        logger.warning(
            "event_fallback_to_log_only",
            event_type=payload["event_type"],
            conversation_id=payload["conversation_id"],
            content_preview=payload["content"][:100],
        )
