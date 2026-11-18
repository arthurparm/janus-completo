import asyncio
import logging
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def seed_graph():
    backend_root_str = str(BACKEND_ROOT)
    if backend_root_str not in sys.path:
        sys.path.append(backend_root_str)
    os.chdir(backend_root_str)

    from app.db.graph import get_graph_db, initialize_graph_db
    from app.repositories.knowledge_repository import KnowledgeRepository
    from app.services.code_analysis_service import code_analysis_service
    from app.services.knowledge_service import KnowledgeService

    logger.info("Initializing Graph Database connection...")
    try:
        await initialize_graph_db()
        graph_db = await get_graph_db()
    except Exception as e:
        logger.error(f"Failed to initialize Graph DB: {e}")
        return

    if not await graph_db.health_check():
        logger.error("Failed to connect to Neo4j. Is it running?")
        return

    logger.info("Graph DB connected. Initializing services...")
    repo = KnowledgeRepository(graph_db)
    service = KnowledgeService(repo)

    # 1. Index Codebase
    logger.info("Starting Codebase Indexation...")
    try:
        # Define o diretório alvo para a pasta 'app' local
        target_dir = os.path.join(backend_root_str, "app")
        logger.info(f"Scanning directory: {target_dir}")

        python_files = code_analysis_service.find_python_files(target_dir)
        logger.info(f"Found {len(python_files)} Python files.")

        if not python_files:
            logger.warning("No python files found! Check the path.")

        total_files = 0
        total_funcs = 0
        total_classes = 0
        all_calls = []

        # Limpa entidades de código anteriores para evitar duplicação/stale data
        logger.info("Clearing existing code entities...")
        await repo.clear_code_entities()

        for i, file_path in enumerate(python_files):
            if i % 10 == 0:
                logger.info(f"Processing file {i + 1}/{len(python_files)}...")

            parser = code_analysis_service.parse_python_file(file_path)
            if parser:
                # Salva estrutura (File, Function, Class e relações CONTAINS)
                await repo.save_code_structure(parser)

                # Coleta chamadas para processamento em lote
                for call in parser.calls:
                    all_calls.append(
                        {
                            "caller_name": call["caller"],
                            "caller_qualified": call.get("caller_qualified"),
                            "callee_name": call["callee"],
                            "callee_qualified": call.get("callee_qualified"),
                            "file_path": file_path,
                        }
                    )
                total_files += 1
                total_funcs += len(parser.functions)
                total_classes += len(parser.classes)

        # Cria relações de chamada (CALLS)
        logger.info(f"Merging {len(all_calls)} calls...")
        await repo.bulk_merge_calls(all_calls)

        logger.info("Indexing Complete.")
        logger.info(f"Files: {total_files}")
        logger.info(f"Functions: {total_funcs}")
        logger.info(f"Classes: {total_classes}")
        logger.info(f"Calls: {len(all_calls)}")

    except Exception as e:
        logger.error(f"Error during indexing: {e}", exc_info=True)

    # 2. Create Default User
    logger.info("Creating Default Admin User in Graph...")
    try:
        async with await graph_db.get_session() as session:
            # Cria nó User (admin)
            query = """
            MERGE (u:User {name: 'Admin'})
            SET u.email = 'admin@janus.system',
                u.created_at = datetime()
            RETURN u
            """
            await session.run(query)
            logger.info("Default User 'Admin' created/merged.")

    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)

    # 3. Stats
    try:
        stats = await service.get_stats()
        logger.info("--- Final Stats ---")
        logger.info(f"Total Nodes: {stats.get('total_nodes')}")
        logger.info(f"Total Relationships: {stats.get('total_relationships')}")

    except Exception as e:
        logger.error(f"Error getting stats: {e}")

    await graph_db.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_graph())
