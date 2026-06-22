import structlog

from app.config import settings
from app.db.graph import get_graph_db
from app.db.vector_store import delete_points_by_filter, get_user_collection_names
from app.repositories.knowledge_repository import get_knowledge_repository

logger = structlog.get_logger(__name__)


class DataRetentionService:
    """
    Service responsible for cleaning up artifacts (Vectors, Graph Nodes)
    when a primary entity (User, Project) is deleted from SQL.
    """

    @staticmethod
    async def cleanup_user_artifacts(user_id: str | int) -> None:
        """
        Removes all data associated with a user from Qdrant and Neo4j.
        This is a 'best effort' background operation or full reset for Single-User.
        """
        normalized_user_id = str(user_id)
        logger.info("Starting cleanup for user", user_id=normalized_user_id)

        # 1. Cleanup Vector Store (Qdrant)
        base_collections = set(get_user_collection_names().values())
        episodic_collection = getattr(
            settings, "QDRANT_COLLECTION_EPISODIC", "janus_episodic_memory"
        )
        target_collections = sorted({*base_collections, str(episodic_collection)})
        for col in target_collections:
            try:
                await delete_points_by_filter(col, {"metadata.user_id": normalized_user_id})
            except Exception as e:
                logger.error("log_error", message=f"Failed to cleanup vector collection {col}: {e}")

        # 2. Cleanup Graph Store (Neo4j)
        try:
            await DataRetentionService._async_graph_cleanup(normalized_user_id)
        except Exception as e:
            logger.error("log_error", message=f"Failed to trigger graph cleanup: {e}")

    @staticmethod
    async def _async_graph_cleanup(user_id: str) -> None:
        try:
            # Manually instantiate dependencies since we are outside DI
            graph_db = await get_graph_db()
            repo = get_knowledge_repository(graph_db)
            await repo.delete_user_data(user_id)
            logger.info("Graph cleanup completed")
        except Exception as e:
            logger.error("log_error", message=f"Async graph cleanup failed: {e}")
