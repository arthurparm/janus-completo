from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.security.request_guard import require_admin_actor
from app.services.data_governance_service import data_governance_service
from app.services.data_purge_service import data_purge_service

router = APIRouter(tags=["Governance"])
logger = structlog.get_logger(__name__)


class ClassificationUpsertRequest(BaseModel):
    user_id: int | None = None
    resource_type: str
    resource_id: str
    classification: str
    retention_policy: str
    retention_days: int | None = None
    metadata: dict[str, Any] | None = None


@router.post("/classifications", summary="Ajusta classificação e retenção manualmente (admin-only)")
async def upsert_classification(payload: ClassificationUpsertRequest, request: Request):
    actor = require_admin_actor(request)
    record_id = data_governance_service.register_manual(
        user_id=payload.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        classification=payload.classification,
        retention_policy=payload.retention_policy,
        retention_days=payload.retention_days,
        metadata=payload.metadata,
    )
    return {"record_id": record_id, "actor_user_id": int(actor)}


class PurgeRunRequest(BaseModel):
    limit: int = 250


@router.post("/purge/run", summary="Executa expurgo auditável (admin-only)")
async def run_purge(payload: PurgeRunRequest, request: Request):
    require_admin_actor(request)
    return await data_purge_service.run_expired_purge(limit=max(1, int(payload.limit)))

