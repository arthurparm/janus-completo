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
    async def cleanup_user_artifacts(user_id: int):
        """
        Removes all data associated with a user from Qdrant and Neo4j.
        This is a 'best effort' background operation.
        """
        if not user_id:
            return

        logger.info("Starting cleanup for user", user_id=user_id)

        # 1. Cleanup Vector Store (Qdrant)
        # Assuming collections are: 'janus_memory', 'janus_knowledge'
        target_collections = ["janus_memory", "janus_knowledge"]
        for col in target_collections:
            try:
                await delete_points_by_filter(col, {"metadata.user_id": user_id})
            except Exception as e:
                logger.error("log_error", message=f"Failed to cleanup vector collection {col} for user {user_id}: {e}")

        # 2. Cleanup Graph Store (Neo4j)
        try:
            await DataRetentionService._async_graph_cleanup(user_id)
        except Exception as e:
            logger.error("log_error", message=f"Failed to trigger graph cleanup for user {user_id}: {e}")

    @staticmethod
    async def _async_graph_cleanup(user_id: int):
        try:
            # Manually instantiate dependencies since we are outside DI
            graph_db = await get_graph_db()
            repo = get_knowledge_repository(graph_db)
            await repo.delete_user_data(user_id)
            logger.info("Graph cleanup completed for user", user_id=user_id)
        except Exception as e:
            logger.error("log_error", message=f"Async graph cleanup failed for user {user_id}: {e}")
