"""
Enhanced Qdrant client with improved timeout, retry, and circuit breaker support.
"""

import asyncio
import structlog
import random
import time
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, SearchParams

from app.config import settings
from app.core.memory.circuit_config import RESILIENCE_CONFIG
from app.core.memory.enhanced_circuit_breaker import circuit_breaker_manager

logger = structlog.get_logger(__name__)


class QdrantOperationTimeout(Exception):
    """Raised when Qdrant operation times out."""

    pass


class QdrantConnectionError(Exception):
    """Raised when Qdrant connection fails."""

    pass


class EnhancedQdrantClient:
    """Enhanced Qdrant client with improved resilience and timeout handling."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        grpc_port: int = 6334,
        prefer_grpc: bool = False,
        **kwargs,
    ):
        """
        Initialize enhanced Qdrant client.

        Args:
            host: Qdrant host
            port: Qdrant HTTP port
            grpc_port: Qdrant gRPC port
            prefer_grpc: Whether to prefer gRPC over HTTP
            **kwargs: Additional arguments for AsyncQdrantClient
        """
        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.prefer_grpc = prefer_grpc

        # Enhanced client configuration
        self.config = RESILIENCE_CONFIG
        self.circuit_breaker = circuit_breaker_manager.get_circuit_breaker("qdrant_search")

        api_key = kwargs.pop("api_key", None)
        if api_key is None:
            cfg_api_key = getattr(settings, "QDRANT_API_KEY", None)
            if hasattr(cfg_api_key, "get_secret_value"):
                cfg_api_key = cfg_api_key.get_secret_value()
            api_key = cfg_api_key

        # Initialize base client with timeout settings
        timeout_config = self.config.qdrant_timeouts
        client_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "grpc_port": grpc_port,
            "prefer_grpc": prefer_grpc,
            "timeout": timeout_config.connection_timeout,
        }
        if api_key:
            client_kwargs["api_key"] = api_key
        client_kwargs.update(kwargs)
        self.client = AsyncQdrantClient(**client_kwargs)

        logger.info(
            "enhanced_qdrant_client_initialized",
            host=host,
            port=port,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
            timeout_config=timeout_config,
        )

    def _calculate_backoff(self, attempt: int, base_backoff: float = 0.5) -> float:
        """Calculate exponential backoff with jitter."""
        config = self.config.retry
        backoff = base_backoff * (config.backoff_multiplier**attempt)

        if config.jitter:
            # Add random jitter (±25%)
            jitter_range = backoff * 0.25
            backoff += random.uniform(-jitter_range, jitter_range)

        return min(backoff, config.max_backoff)

    async def _execute_with_retry(self, operation: str, func: callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic."""
        config = self.config.retry
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                # Calculate timeout for this attempt
                timeout_config = self.config.qdrant_timeouts
                if operation == "search":
                    timeout = timeout_config.search_timeout
                elif operation == "health_check":
                    timeout = timeout_config.health_check_timeout
                else:
                    timeout = timeout_config.read_timeout

                # Add progressive timeout reduction for retries
                if attempt > 0:
                    timeout = min(timeout, timeout * (0.8**attempt))

                # Execute with timeout
                start_time = time.time()
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)

                response_time = time.time() - start_time
                logger.debug(
                    "qdrant_operation_success",
                    operation=operation,
                    attempt=attempt + 1,
                    response_time=response_time,
                    timeout=timeout,
                )

                return result

            except TimeoutError:
                last_exception = QdrantOperationTimeout(f"{operation} timed out after {timeout}s")
                logger.warning(
                    "qdrant_operation_timeout",
                    operation=operation,
                    attempt=attempt + 1,
                    timeout=timeout,
                    max_attempts=config.max_attempts,
                )

            except Exception as e:
                last_exception = QdrantConnectionError(f"{operation} failed: {e!s}")
                logger.warning(
                    "qdrant_operation_error",
                    operation=operation,
                    attempt=attempt + 1,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

            # Calculate backoff before next attempt
            if attempt < config.max_attempts - 1:
                backoff = self._calculate_backoff(attempt, config.initial_backoff)
                logger.info(
                    "qdrant_retry_backoff",
                    operation=operation,
                    attempt=attempt + 1,
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)

        # All attempts failed
        logger.error(
            "qdrant_operation_failed_all_attempts",
            operation=operation,
            attempts=config.max_attempts,
            last_error=str(last_exception),
        )
        raise last_exception

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        query_filter: Filter | None = None,
        search_params: SearchParams | None = None,
        limit: int = 10,
        offset: int | None = None,
        with_payload: bool = True,
        with_vector: bool = False,
        score_threshold: float | None = None,
        **kwargs,
    ) -> list[Any]:
        """
        Enhanced search with circuit breaker and retry logic.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            query_filter: Optional filter
            search_params: Optional search parameters
            limit: Maximum number of results
            offset: Optional offset
            with_payload: Whether to include payload
            with_vector: Whether to include vector
            score_threshold: Optional score threshold
            **kwargs: Additional arguments

        Returns:
            List of search results

        Raises:
            CircuitOpenError: If circuit breaker is open
            QdrantOperationTimeout: If operation times out
            QdrantConnectionError: If connection fails
        """

        # Use circuit breaker for protection
        async def _search_operation():
            return await self._execute_with_retry(
                "search",
                self.client.query_points,
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                search_params=search_params,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vector=with_vector,
                score_threshold=score_threshold,
                **kwargs,
            )

        # Execute through circuit breaker
        return await self.circuit_breaker.call_async(_search_operation)

    async def health_check(self, collection_name: str | None = None) -> bool:
        """
        Perform health check on Qdrant service.

        Args:
            collection_name: Optional collection name to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get server info
            await self._execute_with_retry("health_check", self.client.get_collections)

            # If collection specified, check if it exists
            if collection_name:
                try:
                    await self._execute_with_retry(
                        "health_check", self.client.get_collection, collection_name=collection_name
                    )
                except Exception:
                    logger.warning(
                        "qdrant_collection_not_found_health_check", collection_name=collection_name
                    )
                    return False

            logger.info("qdrant_health_check_success", collection_name=collection_name)
            return True

        except Exception as e:
            logger.error(
                "qdrant_health_check_failed", collection_name=collection_name, error=str(e)
            )
            return False

    async def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get collection information."""
        return await self._execute_with_retry(
            "get_collection", self.client.get_collection, collection_name=collection_name
        )

    async def close(self):
        """Close the client connection."""
        try:
            await self.client.close()
            logger.info("enhanced_qdrant_client_closed")
        except Exception as e:
            logger.warning("error_closing_qdrant_client", error=str(e))

    @property
    def circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return self.circuit_breaker.get_health_status()


# Factory function for creating enhanced clients
async def create_enhanced_qdrant_client(**kwargs) -> EnhancedQdrantClient:
    """Factory function to create and initialize enhanced Qdrant client."""
    client = EnhancedQdrantClient(**kwargs)

    # Perform initial health check
    is_healthy = await client.health_check()
    if not is_healthy:
        logger.warning("qdrant_initial_health_check_failed")

    return client
