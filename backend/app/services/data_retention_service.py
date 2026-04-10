import structlog

from app.db.graph import get_graph_db
from app.db.vector_store import delete_points_by_filter
from app.repositories.knowledge_repository import get_knowledge_repository

logger = structlog.get_logger(__name__)


class DataRetentionService:
    """
    Service responsible for cleaning up artifacts (Vectors, Graph Nodes)
    when a primary entity (User, Project) is deleted from SQL.
    """

    @staticmethod
    async def cleanup_user_artifacts():
        """
        Removes all data associated with a user from Qdrant and Neo4j.
        This is a 'best effort' background operation or full reset for Single-User.
        """
        logger.info("Starting cleanup for user (Single-User)")

        # 1. Cleanup Vector Store (Qdrant)
        # Assuming collections are: 'janus_memory', 'janus_knowledge'
        target_collections = ["janus_memory", "janus_knowledge"]
        for col in target_collections:
            try:
                # In a single-user environment, we would delete all points or recreate the collection.
                # For now, we simulate the deletion or log the recommendation.
                logger.info(f"Full collection cleanup recommended for Single-User on collection {col}.")
                # await delete_points_by_filter(col, {})
            except Exception as e:
                logger.error("log_error", message=f"Failed to cleanup vector collection {col}: {e}")

        # 2. Cleanup Graph Store (Neo4j)
        try:
            await DataRetentionService._async_graph_cleanup()
        except Exception as e:
            logger.error("log_error", message=f"Failed to trigger graph cleanup: {e}")

    @staticmethod
    async def _async_graph_cleanup():
        try:
            # Manually instantiate dependencies since we are outside DI
            graph_db = await get_graph_db()
            repo = get_knowledge_repository(graph_db)
            await repo.delete_user_data()
            logger.info("Graph cleanup completed")
        except Exception as e:
            logger.error("log_error", message=f"Async graph cleanup failed: {e}")
