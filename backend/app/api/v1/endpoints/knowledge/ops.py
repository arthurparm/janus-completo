from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import Depends, HTTPException

from app.services.knowledge_service import KnowledgeService, get_knowledge_service

logger = structlog.get_logger(__name__)


class KnowledgeOpsService:
    def __init__(self, knowledge_service: KnowledgeService):
        self._knowledge_service = knowledge_service

    async def reset_circuit_breaker(self) -> dict[str, str]:
        try:
            from app.core.memory.memory_core import get_memory_db

            memory_db = await get_memory_db()
            memory_db.reset_circuit_breaker()
            return {"message": "Circuit breaker resetado com sucesso"}
        except Exception as exc:
            logger.error("Erro ao resetar circuit breaker", exc_info=exc)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao resetar circuit breaker: {exc!s}",
            ) from exc

    async def get_detailed_health_status(self) -> dict[str, Any]:
        try:
            basic_health = await self._knowledge_service.get_health_status()

            from app.core.memory.memory_core import get_memory_db
            from app.core.memory.qdrant_monitoring import get_qdrant_monitoring_service

            memory_db = await get_memory_db()
            detailed_status = memory_db.get_circuit_breaker_status()
            monitoring_service = get_qdrant_monitoring_service()
            monitoring_status = (
                monitoring_service.get_detailed_metrics() if monitoring_service else None
            )

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": (
                    "healthy"
                    if not detailed_status.get("circuit_breaker_open", False)
                    and not detailed_status.get("offline", False)
                    else "degraded"
                ),
                "basic_health": basic_health,
                "detailed_status": detailed_status,
                "monitoring": monitoring_status,
                "recommendations": detailed_status.get("recommendations", []),
            }
        except Exception as exc:
            logger.error("Erro ao obter status detalhado", exc_info=exc)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao obter status detalhado: {exc!s}",
            ) from exc

    async def publish_consolidation(
        self,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        from app.api.v1.endpoints import knowledge as knowledge_package

        return await knowledge_package.publish_consolidation_task(
            payload,
            correlation_id=correlation_id,
        )


def get_knowledge_ops_service(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeOpsService:
    return KnowledgeOpsService(knowledge_service)
