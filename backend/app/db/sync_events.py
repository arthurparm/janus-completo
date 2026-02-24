import asyncio
import threading

import structlog
from sqlalchemy import event

from app.models.user_models import User
from app.services.data_retention_service import DataRetentionService

logger = structlog.get_logger(__name__)


def _log_background_task_failure(task: asyncio.Task, user_id: int) -> None:
    try:
        _ = task.result()
    except Exception as exc:
        logger.error("Background user cleanup task failed.", user_id=user_id, exc_info=exc)


def _run_cleanup_in_thread(user_id: int) -> None:
    try:
        asyncio.run(DataRetentionService.cleanup_user_artifacts(user_id))
    except Exception as exc:
        logger.error("Threaded user cleanup failed.", user_id=user_id, exc_info=exc)


def _dispatch_user_cleanup(user_id: int) -> None:
    if not user_id:
        return

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(DataRetentionService.cleanup_user_artifacts(user_id))
        task.add_done_callback(lambda t: _log_background_task_failure(t, user_id))
    except RuntimeError:
        thread = threading.Thread(
            target=_run_cleanup_in_thread,
            args=(user_id,),
            daemon=True,
            name=f"user-cleanup-{user_id}",
        )
        thread.start()


def register_cleanup_events():
    """
    Registers SQLAlchemy events to enforce data consistency
    across Polyglot persistence (SQL -> Vector -> Graph).
    """

    @event.listens_for(User, 'after_delete')
    def receive_after_delete(mapper, connection, target):
        """
        Triggered after a User row is deleted.
        """
        user_id = target.id
        logger.info("log_info", message=f"User {user_id} deleted from DB. Triggering artifact cleanup.")

        _dispatch_user_cleanup(user_id)

    logger.info("Data Retention Listeners Registered.")
