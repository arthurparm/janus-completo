from collections.abc import AsyncIterator, Mapping
from typing import Any, Protocol

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agents.graph_orchestrator import (
    GRAPH_SCHEMA_VERSION,
    get_graph_checkpointer,
)
from app.core.security.request_guard import require_service_actor
from app.db.postgres_config import postgres_db

router = APIRouter(tags=["Admin"], prefix="/admin/checkpoints")
logger = structlog.get_logger(__name__)


class CheckpointSnapshot(Protocol):
    config: Mapping[str, Any]
    checkpoint: Mapping[str, Any]


class CheckpointerReader(Protocol):
    def alist(
        self,
        config: Mapping[str, Any] | None,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointSnapshot]: ...


class PurgeIncompatibleRequest(BaseModel):
    execute: bool = False
    expected_schema_version: int | None = Field(default=None, ge=1)
    max_checkpoints: int = Field(default=1_000, ge=1, le=10_000)


class PurgeIncompatibleResponse(BaseModel):
    schema_version: int
    scanned_checkpoints: int
    scanned_threads: int
    incompatible_threads_count: int
    deleted_threads_count: int
    scan_complete: bool
    executed: bool
    message: str


class _ScanResult(BaseModel):
    scanned_checkpoints: int
    scanned_threads: int
    incompatible_thread_ids: list[str]
    complete: bool


def _snapshot_schema_version(snapshot: CheckpointSnapshot) -> int | None:
    channel_values = snapshot.checkpoint.get("channel_values")
    if not isinstance(channel_values, Mapping):
        return None
    raw_version = channel_values.get("schema_version")
    if type(raw_version) is int:
        return raw_version
    if isinstance(raw_version, str):
        try:
            return int(raw_version)
        except ValueError:
            return None
    return None


async def _scan_latest_threads(
    checkpointer: CheckpointerReader, *, max_checkpoints: int
) -> _ScanResult:
    latest_versions: dict[str, int | None] = {}
    scanned_checkpoints = 0
    complete = True

    async for snapshot in checkpointer.alist(None, limit=max_checkpoints + 1):
        scanned_checkpoints += 1
        if scanned_checkpoints > max_checkpoints:
            complete = False
            break

        configurable = snapshot.config.get("configurable")
        if not isinstance(configurable, Mapping):
            continue
        thread_id = str(configurable.get("thread_id") or "").strip()
        if not thread_id or thread_id in latest_versions:
            continue
        latest_versions[thread_id] = _snapshot_schema_version(snapshot)

    incompatible = sorted(
        thread_id
        for thread_id, version in latest_versions.items()
        if version != GRAPH_SCHEMA_VERSION
    )
    return _ScanResult(
        scanned_checkpoints=min(scanned_checkpoints, max_checkpoints),
        scanned_threads=len(latest_versions),
        incompatible_thread_ids=incompatible,
        complete=complete,
    )


async def _delete_threads_atomically(
    session: AsyncSession, thread_ids: list[str]
) -> None:
    if not thread_ids:
        return
    params = {"thread_ids": thread_ids}
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        statement = text(
            f"DELETE FROM {table} WHERE thread_id IN :thread_ids"
        ).bindparams(bindparam("thread_ids", expanding=True))
        await session.execute(statement, params)


@router.post("/purge-incompatible", response_model=PurgeIncompatibleResponse)
async def purge_incompatible_checkpoints(
    payload: PurgeIncompatibleRequest,
    request: Request,
    checkpointer: CheckpointerReader | None = Depends(get_graph_checkpointer),
) -> PurgeIncompatibleResponse:
    """Inspeciona ou remove atomicamente threads com estado de grafo incompatível."""
    require_service_actor(request)
    if checkpointer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Postgres graph checkpointer is unavailable",
        )

    try:
        scan = await _scan_latest_threads(
            checkpointer, max_checkpoints=payload.max_checkpoints
        )
    except Exception as exc:
        logger.exception("checkpoint_compatibility_scan_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkpoint compatibility scan failed",
        ) from exc

    incompatible_count = len(scan.incompatible_thread_ids)
    if not payload.execute:
        return PurgeIncompatibleResponse(
            schema_version=GRAPH_SCHEMA_VERSION,
            scanned_checkpoints=scan.scanned_checkpoints,
            scanned_threads=scan.scanned_threads,
            incompatible_threads_count=incompatible_count,
            deleted_threads_count=0,
            scan_complete=scan.complete,
            executed=False,
            message="Dry run completed; no checkpoint data was deleted",
        )

    if payload.expected_schema_version != GRAPH_SCHEMA_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="expected_schema_version must match the active graph schema version",
        )
    if not scan.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkpoint scan limit reached; increase max_checkpoints before deletion",
        )

    try:
        async with postgres_db.get_session_async() as session:
            await _delete_threads_atomically(session, scan.incompatible_thread_ids)
    except Exception as exc:
        logger.exception(
            "checkpoint_incompatible_purge_failed",
            incompatible_threads_count=incompatible_count,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkpoint purge failed and was rolled back",
        ) from exc

    logger.warning(
        "checkpoint_incompatible_threads_purged",
        deleted_threads_count=incompatible_count,
        schema_version=GRAPH_SCHEMA_VERSION,
    )
    return PurgeIncompatibleResponse(
        schema_version=GRAPH_SCHEMA_VERSION,
        scanned_checkpoints=scan.scanned_checkpoints,
        scanned_threads=scan.scanned_threads,
        incompatible_threads_count=incompatible_count,
        deleted_threads_count=incompatible_count,
        scan_complete=True,
        executed=True,
        message="Incompatible checkpoint threads were deleted atomically",
    )
