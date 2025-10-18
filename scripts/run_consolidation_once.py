import asyncio
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ops.run_consolidation_once")


async def main(limit: int = 25, min_score: float = 0.0):
    t0 = time.perf_counter()
    try:
        from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator
        logger.info("[Consolidation] Inicializando consolidator…")
        await knowledge_consolidator._initialize()
        logger.info("[Consolidation] Executando consolidação em lote…")
        stats = await knowledge_consolidator.consolidate_batch(limit=limit, min_score=min_score)
        print(json.dumps(stats))
        logger.info(
            f"[Consolidation] Concluída: {stats.get('successful', 0)}/{stats.get('total_processed', 0)} em {stats.get('elapsed_seconds', 0.0):.2f}s"
        )
    except Exception as e:
        logger.error(f"[Consolidation] Erro: {e}", exc_info=True)
    finally:
        logger.info(f"[Consolidation] Tempo total: {time.perf_counter() - t0:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())