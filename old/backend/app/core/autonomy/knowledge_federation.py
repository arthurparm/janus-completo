import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class KnowledgeFederation:
    CHANNEL = "janus:federation:knowledge"

    def __init__(self) -> None:
        self._config_enabled = False
        self._instance_id = hashlib.sha256(str(datetime.now(timezone.utc)).encode()).hexdigest()[:8]

    async def publish_entity(self, entity: dict[str, Any], redis_manager: Any = None) -> None:
        if not self._config_enabled or redis_manager is None:
            return
        try:
            payload = {
                "entity": entity,
                "source_instance": self._instance_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signature": hashlib.sha256(json.dumps(entity, sort_keys=True).encode()).hexdigest(),
            }
            if redis_manager.client:
                await redis_manager.publish(self.CHANNEL, json.dumps(payload))
        except Exception:
            pass

    async def on_entity_received(self, payload: dict[str, Any], knowledge_service: Any = None) -> None:
        if not self._config_enabled or knowledge_service is None:
            return
        entity = payload.get("entity", {})
        if entity.get("quarantine_reason"):
            return
        expected = hashlib.sha256(json.dumps(entity, sort_keys=True).encode()).hexdigest()
        if payload.get("signature") != expected:
            logger.warning("federation_signature_mismatch")
            return
        try:
            await knowledge_service.merge_federated_entity(entity)
        except Exception:
            pass


knowledge_federation = KnowledgeFederation()
