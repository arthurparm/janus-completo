
import asyncio
import json
from typing import Any

import structlog

from app.config import settings
from app.core.infrastructure.redis_manager import get_redis_manager

logger = structlog.get_logger(__name__)


class ConfigService:
    """
    Service for managing configuration hot-reloads via Redis Pub/Sub.
    Allows dynamic updates to AppSettings across all running instances.
    """

    def __init__(self):
        self.redis = get_redis_manager()
        self.channel_name = "janus:config:updates"
        self._listener_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Starts the background listener task."""
        if self._running:
            return
        
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("ConfigService listener started.", channel=self.channel_name)

    async def stop(self):
        """Stops the background listener task."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
            logger.info("ConfigService listener stopped.")

    async def _listen_loop(self):
        """Main loop for listening to Redis Pub/Sub messages."""
        while self._running:
            try:
                # Get a dedicated pubsub connection
                redis_client = await self.redis.get_client()
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(self.channel_name)

                async for message in pubsub.listen():
                    if not self._running:
                        break
                        
                    if message["type"] == "message":
                        await self._handle_update(message["data"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("ConfigService listener error", error=str(e))
                await asyncio.sleep(5)  # Backoff before reconnecting

    async def _handle_update(self, data: bytes | str):
        """Parses update message and applies changes to settings."""
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            
            payload = json.loads(data)
            logger.info("Received config update event", items=len(payload))
            
            # Apply update to the singleton settings object
            settings.update(payload)
            
        except json.JSONDecodeError:
            logger.error("Received invalid JSON in config update")
        except Exception as e:
            logger.error("Failed to apply config update", error=str(e))

    async def update_config(self, updates: dict[str, Any]):
        """
        Updates configuration locally and publishes event to other instances.
        
        Args:
            updates: Dictionary with new configuration values.
        """
        # 1. Update local instance immediately
        settings.update(updates)
        logger.info("Local configuration updated", keys=list(updates.keys()))

        # 2. Publish to Redis for other instances
        try:
            message = json.dumps(updates)
            await self.redis.publish(self.channel_name, message)
        except Exception as e:
            logger.error("Failed to publish config update to Redis", error=str(e))
            # Note: We don't rollback local change because Redis failure shouldn't block local admin action,
            # but consistency is compromised until Redis is back.


_config_service: ConfigService | None = None

def get_config_service() -> ConfigService:
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
