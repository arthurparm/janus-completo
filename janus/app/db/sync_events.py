import structlog
from sqlalchemy import event

from app.models.user_models import User
from app.services.data_retention_service import DataRetentionService

logger = structlog.get_logger(__name__)

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
        logger.info(f"User {user_id} deleted from DB. Triggering artifact cleanup.")

        # Dispatch cleanup
        # Note: This is a synchronous callback.
        # fastAPI/Uvicorn runs in an async loop, so we can schedule the task.
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Fire and forget (or track via background tasks if possible)
            loop.create_task(DataRetentionService.cleanup_user_artifacts(user_id))
        except RuntimeError:
            # We might be in a script or non-async context.
            # For now, we log usage warning.
            logger.warning(f"Could not schedule async cleanup for User {user_id} (No Event Loop).")

    logger.info("Data Retention Listeners Registered.")
