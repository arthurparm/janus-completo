import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import redis.asyncio as redis
import structlog
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from app.config import settings

logger = structlog.get_logger(__name__)


class RedisManager:
    """
    Gerenciador global de conexões Redis com suporte a pooling assíncrono,
    retries automáticos e serialização.
    """

    _instance: "RedisManager | None" = None
    _pool: redis.ConnectionPool | None = None

    def __init__(self):
        self._client: redis.Redis | None = None

    @classmethod
    def get_instance(cls) -> "RedisManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self):
        """Inicializa o pool de conexões Redis."""
        if not settings.REDIS_ENABLED:
            logger.info("Redis is disabled specifically by config.")
            return

        if self._client is not None:
            return

        url = settings.REDIS_URL
        logger.info(f"Initializing Redis connection pool at {url}")

        retry_strategy = Retry(
            ExponentialBackoff(cap=2.0, base=0.5),
            3,  # Max retries
        )

        try:
            # Usando from_url com pooling e retry config
            self._client = redis.Redis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
                retry=retry_strategy,
                retry_on_error=[ConnectionError, TimeoutError, ConnectionRefusedError],
                health_check_interval=30,
            )
            
            # Fail-fast ping check
            await self._client.ping()
            logger.info("Redis connection established successfully.")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            # Em modo 'Fail Open', não crashamos a app, mas o client fica None ou inoperante.
            # Se for strict, deveríamos dar raise.
            # Aqui vamos deixar o client operante para sofrer retries subsequentes ou falhar nas chamadas.

    async def close(self):
        """Fecha o pool de conexões."""
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed.")

    @property
    def client(self) -> redis.Redis:
        """Retorna o cliente raw, lança erro se não inicializado."""
        if self._client is None:
            raise RuntimeError("RedisManager not initialized or Redis disabled.")
        return self._client

    async def ping(self) -> bool:
        """Verifica saúde da conexão."""
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def get(self, key: str) -> Any:
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            return await self.client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")
            return False
            
    async def publish(self, channel: str, message: str) -> int:
        try:
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.error(f"Redis publish failed to {channel}: {e}")
            return 0

    @asynccontextmanager
    async def pubsub(self) -> AsyncGenerator[redis.client.PubSub, None]:
        """Context manager para pubsub."""
        if not self._client:
             raise RuntimeError("Redis not initialized")
        ps = self._client.pubsub()
        try:
            yield ps
        finally:
            await ps.close()

# Singleton global accessor
redis_manager = RedisManager.get_instance()

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Dependency for FastAPI"""
    if redis_manager.client:
        yield redis_manager.client
