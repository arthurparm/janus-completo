import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.autonomy_lock_service import AutonomyLockService


class _FakeLockRepo:
    def __init__(self):
        self.row = None

    def try_acquire(self, *, scope_key, owner_id, ttl_seconds, metadata_json=None):
        now = datetime.utcnow()
        expires = now + timedelta(seconds=ttl_seconds)
        if self.row is None or self.row.expires_at <= now:
            self.row = SimpleNamespace(
                scope_key=scope_key,
                owner_id=owner_id,
                acquired_at=now,
                heartbeat_at=now,
                expires_at=expires,
                metadata_json=metadata_json,
            )
            return True, self.row
        if self.row.owner_id == owner_id:
            self.row.heartbeat_at = now
            self.row.expires_at = expires
            return True, self.row
        return False, self.row

    def renew(self, *, scope_key, owner_id, ttl_seconds):
        now = datetime.utcnow()
        if self.row is None or self.row.scope_key != scope_key or self.row.owner_id != owner_id:
            return False, self.row
        self.row.heartbeat_at = now
        self.row.expires_at = now + timedelta(seconds=ttl_seconds)
        return True, self.row

    def release(self, *, scope_key, owner_id):
        if self.row and self.row.scope_key == scope_key and self.row.owner_id == owner_id:
            self.row = None
            return True
        return False

    def get(self, scope_key):
        return self.row if self.row and self.row.scope_key == scope_key else None


def test_make_scope_key_variants():
    assert AutonomyLockService.make_scope_key(user_id=None, project_id=None) == "global"
    assert AutonomyLockService.make_scope_key(user_id="u1", project_id=None) == "user:u1"
    assert AutonomyLockService.make_scope_key(user_id=None, project_id="p1") == "project:p1"
    assert (
        AutonomyLockService.make_scope_key(user_id="u1", project_id="p1")
        == "user:u1:project:p1"
    )


def test_lock_service_try_acquire_renew_release():
    repo = _FakeLockRepo()
    service = AutonomyLockService(repo=repo)
    owner = "owner-1"
    scope = "global"

    ok, state = service.try_acquire(scope_key=scope, owner_id=owner, ttl_seconds=30, metadata={})
    assert ok is True
    assert state.lease_held is True
    assert state.owner_id == owner

    renewed, renewed_state = service.renew(scope_key=scope, owner_id=owner, ttl_seconds=30)
    assert renewed is True
    assert renewed_state.lease_held is True

    released = service.release(scope_key=scope, owner_id=owner)
    assert released is True
    final_state = service.get(scope_key=scope)
    assert final_state.lease_held is False
