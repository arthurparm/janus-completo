from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import admin_checkpoints
from app.core.agents.graph_orchestrator import GRAPH_SCHEMA_VERSION
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod


class _Checkpointer:
    def __init__(self, snapshots):
        self.snapshots = snapshots

    async def alist(self, _config, *, limit=None):
        for snapshot in self.snapshots[:limit]:
            yield snapshot


def _snapshot(thread_id: str, version):
    return SimpleNamespace(
        config={"configurable": {"thread_id": thread_id}},
        checkpoint={"channel_values": {"schema_version": version}},
    )


def _service_request():
    actor = ActorContext.authenticated(
        actor_id="janus-ops",
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-purge",
        actor_type=ActorType.SERVICE,
        scopes=("ops:execute",),
    )
    return SimpleNamespace(state=SimpleNamespace(actor_context=actor))


def _human_request():
    actor = ActorContext.authenticated(
        actor_id="user-1",
        roles=("ADMIN",),
        auth_method=AuthMethod.OIDC,
        trace_id="trace-human",
    )
    return SimpleNamespace(state=SimpleNamespace(actor_context=actor))


@pytest.mark.asyncio
async def test_dry_run_uses_latest_state_per_thread_and_deletes_nothing():
    checkpointer = _Checkpointer(
        [
            _snapshot("current", GRAPH_SCHEMA_VERSION),
            _snapshot("current", None),
            _snapshot("legacy", None),
        ]
    )

    response = await admin_checkpoints.purge_incompatible_checkpoints(
        admin_checkpoints.PurgeIncompatibleRequest(),
        _service_request(),
        checkpointer,
    )

    assert response.executed is False
    assert response.scanned_threads == 2
    assert response.incompatible_threads_count == 1
    assert response.deleted_threads_count == 0


@pytest.mark.asyncio
async def test_execute_requires_matching_schema_confirmation():
    with pytest.raises(HTTPException) as exc_info:
        await admin_checkpoints.purge_incompatible_checkpoints(
            admin_checkpoints.PurgeIncompatibleRequest(
                execute=True, expected_schema_version=GRAPH_SCHEMA_VERSION + 1
            ),
            _service_request(),
            _Checkpointer([_snapshot("legacy", None)]),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_human_admin_cannot_invoke_service_only_purge():
    with pytest.raises(HTTPException) as exc_info:
        await admin_checkpoints.purge_incompatible_checkpoints(
            admin_checkpoints.PurgeIncompatibleRequest(),
            _human_request(),
            _Checkpointer([]),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_execute_blocks_incomplete_scan():
    with pytest.raises(HTTPException) as exc_info:
        await admin_checkpoints.purge_incompatible_checkpoints(
            admin_checkpoints.PurgeIncompatibleRequest(
                execute=True,
                expected_schema_version=GRAPH_SCHEMA_VERSION,
                max_checkpoints=1,
            ),
            _service_request(),
            _Checkpointer(
                [_snapshot("legacy-1", None), _snapshot("legacy-2", None)]
            ),
        )

    assert exc_info.value.status_code == 409
    assert "scan limit" in exc_info.value.detail


@pytest.mark.asyncio
async def test_execute_deletes_all_checkpoint_tables_in_one_session(monkeypatch):
    session = AsyncMock()

    class _SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        admin_checkpoints.postgres_db,
        "get_session_async",
        lambda: _SessionContext(),
    )

    response = await admin_checkpoints.purge_incompatible_checkpoints(
        admin_checkpoints.PurgeIncompatibleRequest(
            execute=True, expected_schema_version=GRAPH_SCHEMA_VERSION
        ),
        _service_request(),
        _Checkpointer([_snapshot("legacy", None)]),
    )

    assert response.executed is True
    assert response.deleted_threads_count == 1
    assert session.execute.await_count == 3
    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert "DELETE FROM checkpoint_writes" in statements[0]
    assert "DELETE FROM checkpoint_blobs" in statements[1]
    assert "DELETE FROM checkpoints" in statements[2]
