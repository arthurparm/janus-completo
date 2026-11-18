import asyncio
import logging
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def cleanup_graph_synonyms() -> None:
    backend_root_str = str(BACKEND_ROOT)
    if backend_root_str not in sys.path:
        sys.path.append(backend_root_str)
    os.chdir(backend_root_str)

    from app.db.graph import get_graph_db, initialize_graph_db
    from app.core.memory.graph_guardian import ENTITY_PROPERTY_SYNONYMS

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
