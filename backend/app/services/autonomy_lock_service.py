from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.infrastructure.redis_manager import get_redis_manager
from app.repositories.autonomy_lock_repository import AutonomyLockRepository


@dataclass
class AutonomyLeaseState:
    scope_key: str
    owner_id: str | None
    lease_held: bool
    acquired_at: datetime | None
    heartbeat_at: datetime | None
    expires_at: datetime | None


class AutonomyLockService:
    def __init__(self, repo: AutonomyLockRepository | None = None):
        self._repo = repo or AutonomyLockRepository()
        self._leases: dict[str, dict[str, Any]] = {}

    @staticmethod
    def make_owner_id() -> str:
        return f"autonomy-loop:{uuid.uuid4().hex}"

    @staticmethod
    def make_scope_key(*, user_id: str | None, project_id: str | None) -> str:
        if user_id and project_id:
            return f"user:{user_id}:project:{project_id}"
        if project_id:
            return f"project:{project_id}"
        if user_id:
            return f"user:{user_id}"
        return "global"

    async def acquire(self, scope: str, owner_id: str, ttl: int) -> bool:
        redis = get_redis_manager()
        try:
            await redis.initialize()
            if await redis.ping():
                key = f"janus:autonomy:lease:{scope}"
                acquired = await redis.client.set(key, owner_id, nx=True, px=ttl * 1000)
                if acquired:
                    self._leases[scope] = {"owner": owner_id, "expires": time.time() + ttl}
                    return True
        except Exception:
            pass
        if scope not in self._leases or time.time() > self._leases[scope]["expires"]:
            self._leases[scope] = {"owner": owner_id, "expires": time.time() + ttl}
            return True
        return False

    def try_acquire(
        self,
        *,
        scope_key: str,
        owner_id: str,
        ttl_seconds: int,
        metadata: dict | None = None,
    ) -> tuple[bool, AutonomyLeaseState]:
        ok, row = self._repo.try_acquire(
            scope_key=scope_key,
            owner_id=owner_id,
            ttl_seconds=ttl_seconds,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        return ok, self._to_state(scope_key, owner_id, ok, row)

    def renew(self, *, scope_key: str, owner_id: str, ttl_seconds: int) -> tuple[bool, AutonomyLeaseState]:
        ok, row = self._repo.renew(scope_key=scope_key, owner_id=owner_id, ttl_seconds=ttl_seconds)
        return ok, self._to_state(scope_key, owner_id, ok, row)

    def release(self, *, scope_key: str, owner_id: str) -> bool:
        released = self._repo.release(scope_key=scope_key, owner_id=owner_id)
        self._leases.pop(scope_key, None)
        return released

    def get(self, *, scope_key: str) -> AutonomyLeaseState:
        row = self._repo.get(scope_key)
        held = bool(row and row.expires_at and row.expires_at > datetime.utcnow())
        return self._to_state(scope_key, getattr(row, "owner_id", None), held, row)

    @staticmethod
    def _to_state(scope_key: str, owner_id: str | None, held: bool, row) -> AutonomyLeaseState:
        return AutonomyLeaseState(
            scope_key=scope_key,
            owner_id=getattr(row, "owner_id", owner_id),
            lease_held=held,
            acquired_at=getattr(row, "acquired_at", None),
            heartbeat_at=getattr(row, "heartbeat_at", None),
            expires_at=getattr(row, "expires_at", None),
        )
