from fastapi import APIRouter

from .consolidation import router as consolidation_router
from .experimental import router as experimental_router
from .graph import router as graph_router
from .health import router as health_router
from .spaces import router as spaces_router


async def publish_consolidation_task(payload, correlation_id=None):
    from app.core.workers.async_consolidation_worker import (
        publish_consolidation_task as worker_publish_consolidation_task,
    )

    return await worker_publish_consolidation_task(
        payload,
        correlation_id=correlation_id,
    )


router = APIRouter(tags=["Knowledge"])
router.include_router(graph_router)
router.include_router(health_router)
router.include_router(experimental_router)
router.include_router(consolidation_router)
router.include_router(spaces_router)

__all__ = ["publish_consolidation_task", "router"]
