import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ops.reset_and_consolidate")


async def reset_neo4j():
    from app.db.graph import initialize_graph_db, get_graph_db

    await initialize_graph_db()
    db = await get_graph_db()

    logger.info("[Neo4j] Health check antes do reset…")
    ok_before = await db.health_check()
    logger.info(f"[Neo4j] Saúde: {'healthy' if ok_before else 'unhealthy'}")

    logger.info("[Neo4j] Limpando todos os nós e relações…")
    # Remove todos nós e relações
    await db.execute("MATCH (n) DETACH DELETE n", operation="reset_graph")

    # Recria ontologia básica
    try:
        # Limpa cache local de tipos conhecidos e re-inicializa ontologia
        db._known_relationship_types.clear()  # type: ignore[attr-defined]
        await db._initialize_ontology()  # type: ignore[attr-defined]
        logger.info("[Neo4j] Ontologia re-inicializada.")
    except Exception as e:
        logger.warning(f"[Neo4j] Falha ao re-inicializar ontologia: {e}")

    ok_after = await db.health_check()
    logger.info(f"[Neo4j] Saúde pós-reset: {'healthy' if ok_after else 'unhealthy'}")


async def run_consolidation(limit: int = 25):
    logger.info("[Consolidation] Inicializando…")
    t0 = time.perf_counter()
    try:
        # Checa Qdrant readiness rapidamente
        from app.db.vector_store import check_qdrant_readiness, get_or_create_collection
        from app.config import settings
        try:
            check_qdrant_readiness()
            logger.info("[Qdrant] OK.")
            # Garante coleção padrão
            get_or_create_collection(settings.QDRANT_COLLECTION_EPISODIC)
        except Exception as e:
            logger.warning(f"[Qdrant] Readiness falhou ou coleção ausente: {e}")

        # Executa consolidação
        from app.core.memory.knowledge_graph_manager import aconsolidate_experiences_into_graph
        res = await aconsolidate_experiences_into_graph(limit=limit)
        logger.info(res.get("summary", "Consolidação executada."))
    except Exception as e:
        logger.error(f"[Consolidation] Erro ao consolidar: {e}", exc_info=True)
    finally:
        logger.info(f"[Consolidation] Tempo total: {time.perf_counter() - t0:.2f}s")


async def verify_all():
    logger.info("[Verify] Verificando saúde agregada…")
    # Broker
    try:
        from app.core.infrastructure.message_broker import get_broker
        broker = await get_broker()
        ok = await broker.health_check()
        logger.info(f"[RabbitMQ] Saúde: {'healthy' if ok else 'unhealthy'}")
    except Exception as e:
        logger.warning(f"[RabbitMQ] Erro na verificação: {e}")

    # LLM Manager
    try:
        from app.core.monitoring.health_monitor import check_llm_manager_health
        res = await check_llm_manager_health()
        logger.info(f"[LLM] {res.get('status')}: {res.get('message')}")
    except Exception as e:
        logger.warning(f"[LLM] Erro na verificação: {e}")

    # Neo4j
    try:
        from app.db.graph import get_graph_db
        db = await get_graph_db()
        ok = await db.health_check()
        logger.info(f"[Neo4j] Saúde: {'healthy' if ok else 'unhealthy'}")
    except Exception as e:
        logger.warning(f"[Neo4j] Erro na verificação: {e}")

    # Qdrant
    try:
        from app.db.vector_store import check_qdrant_readiness
        try:
            check_qdrant_readiness()
            logger.info("[Qdrant] Saúde: healthy")
        except Exception as e:
            logger.warning(f"[Qdrant] Saúde: unhealthy ({e})")
    except Exception as e:
        logger.warning(f"[Qdrant] Erro na verificação: {e}")


async def main():
    await verify_all()
    await reset_neo4j()
    await run_consolidation(limit=25)
    await verify_all()


if __name__ == "__main__":
    asyncio.run(main())