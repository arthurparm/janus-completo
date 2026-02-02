import asyncio
import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def cleanup_graph_synonyms() -> None:
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    os.chdir(parent_dir)

    from app.core.memory.graph_guardian import ENTITY_PROPERTY_SYNONYMS
    from app.db.graph import get_graph_db, initialize_graph_db

    logger.info("Initializing Graph Database connection for synonym cleanup...")
    try:
        await initialize_graph_db()
        graph_db = await get_graph_db()
    except Exception as e:
        logger.error(f"Failed to initialize Graph DB: {e}")
        return

    ok = await graph_db.health_check()
    if not ok:
        logger.error("Neo4j is not healthy or not reachable. Aborting synonym cleanup.")
        return

    total_updated = 0
    for label, mappings in ENTITY_PROPERTY_SYNONYMS.items():
        logger.info(f"Running synonym cleanup for {label} nodes...")
        updated = await graph_db.cleanup_synonym_properties(label, mappings)
        logger.info(f"{label} nodes updated: {updated}")
        total_updated += updated

    logger.info(f"Synonym cleanup finished. Total nodes updated: {total_updated}.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cleanup_graph_synonyms())
