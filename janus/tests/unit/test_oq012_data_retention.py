import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.sync_events import _dispatch_user_cleanup
from app.services.data_retention_service import DataRetentionService


@pytest.mark.asyncio
async def test_cleanup_user_artifacts_awaits_vector_and_graph_cleanup():
    with (
        patch(
            "app.services.data_retention_service.delete_points_by_filter", new_callable=AsyncMock
        ) as mock_delete,
        patch.object(
            DataRetentionService, "_async_graph_cleanup", new_callable=AsyncMock
        ) as mock_graph_cleanup,
    ):
        await DataRetentionService.cleanup_user_artifacts(123)

    assert mock_delete.await_count == 2
    mock_delete.assert_any_await("janus_memory", {"metadata.user_id": 123})
    mock_delete.assert_any_await("janus_knowledge", {"metadata.user_id": 123})
    mock_graph_cleanup.assert_awaited_once_with(123)


def test_dispatch_user_cleanup_uses_running_loop_task():
    loop = MagicMock()
    task = MagicMock()
    loop.create_task.return_value = task

    with patch("app.db.sync_events.asyncio.get_running_loop", return_value=loop):
        _dispatch_user_cleanup(77)

    loop.create_task.assert_called_once()
    created_coro = loop.create_task.call_args.args[0]
    assert asyncio.iscoroutine(created_coro)
    created_coro.close()
    task.add_done_callback.assert_called_once()


def test_dispatch_user_cleanup_falls_back_to_thread_without_loop():
    thread_instance = MagicMock()
    thread_cls = MagicMock(return_value=thread_instance)

    with (
        patch(
            "app.db.sync_events.asyncio.get_running_loop",
            side_effect=RuntimeError("no event loop"),
        ),
        patch("app.db.sync_events.threading.Thread", thread_cls),
    ):
        _dispatch_user_cleanup(88)

    thread_cls.assert_called_once()
    thread_instance.start.assert_called_once()
