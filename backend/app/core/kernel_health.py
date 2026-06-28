import asyncio

import structlog
from sqlalchemy import text

from app.core.infrastructure.redis_manager import RedisManager
from app.db.graph import get_graph_db
from app.db.postgres_config import postgres_db

logger = structlog.get_logger(__name__)


async def check_neo4j() -> dict:
    start = asyncio.get_event_loop().time()
    try:
        db = await get_graph_db()
        session = await db.get_session()
        try:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            ok = bool(record and record.get("ok") == 1)
            latency = asyncio.get_event_loop().time() - start
            if ok:
                return {
                    "status": "healthy",
                    "message": "Neo4j connection is operational",
                    "details": {"latency_seconds": round(latency, 3)},
                }
            return {
                "status": "degraded",
                "message": "Neo4j returned unexpected result",
                "details": {"latency_seconds": round(latency, 3)},
            }
        finally:
            await session.close()
    except Exception as e:
        latency = asyncio.get_event_loop().time() - start
        logger.warning("neo4j_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"Neo4j health check failed: {e!s}",
            "details": {"latency_seconds": round(latency, 3)},
        }


async def check_postgres() -> dict:
    start = asyncio.get_event_loop().time()
    try:
        async with postgres_db.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = asyncio.get_event_loop().time() - start
        return {
            "status": "healthy",
            "message": "PostgreSQL connection is operational",
            "details": {"latency_seconds": round(latency, 3)},
        }
    except Exception as e:
        latency = asyncio.get_event_loop().time() - start
        logger.warning("postgres_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"PostgreSQL health check failed: {e!s}",
            "details": {"latency_seconds": round(latency, 3)},
        }


async def check_redis() -> dict:
    start = asyncio.get_event_loop().time()
    try:
        manager = RedisManager.get_instance()
        ok = await manager.ping()
        latency = asyncio.get_event_loop().time() - start
        if ok:
            return {
                "status": "healthy",
                "message": "Redis connection is operational",
                "details": {"latency_seconds": round(latency, 3)},
            }
        return {
            "status": "degraded",
            "message": "Redis ping returned False",
            "details": {"latency_seconds": round(latency, 3)},
        }
    except Exception as e:
        latency = asyncio.get_event_loop().time() - start
        logger.warning("redis_health_check_failed", error=str(e))
        return {
            "status": "degraded",
            "message": f"Redis health check failed: {e!s}",
            "details": {"latency_seconds": round(latency, 3)},
        }
