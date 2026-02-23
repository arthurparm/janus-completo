"""
FallbackChain pattern for executing strategies with hierarchical fallbacks.
Provides observability, metrics, and circuit breaker integration.
"""

from typing import Any, Callable, TypeVar
import asyncio
import structlog
from prometheus_client import Counter

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Metrics
FALLBACK_COUNTER = Counter(
    "fallback_invocations_total",
    "Number of fallback invocations",
    ["component", "level", "success"],
)


class FallbackChain:
    """
    Executes strategies in order until one succeeds.

    Features:
    - Hierarchical fallback execution
    - Metrics tracking (Prometheus)
    - Structured logging
    - Circuit breaker awareness

    Example:
        ```python
        chain = FallbackChain([
            primary_strategy,
            secondary_strategy,
            minimal_fallback
        ], component_name="prompt_build")

        result = await chain.execute(args...)
        ```
    """

    def __init__(
        self,
        strategies: list[Callable],
        component_name: str,
        circuit_breaker: Any | None = None,
    ):
        """
        Initialize fallback chain.

        Args:
            strategies: List of callables to try in order
            component_name: Name for metrics/logging (e.g. "prompt_build")
            circuit_breaker: Optional circuit breaker instance
        """
        if not strategies:
            raise ValueError("At least one strategy is required")

        self.strategies = strategies
        self.component_name = component_name
        self.circuit_breaker = circuit_breaker

    async def execute(self, *args, **kwargs) -> T:
        """
        Execute strategies with fallback hierarchy.

        Returns:
            Result from first successful strategy

        Raises:
            Exception: If all strategies fail
        """
        last_error = None

        for i, strategy in enumerate(self.strategies):
            try:
                # Check circuit breaker for primary strategy
                if i == 0 and self.circuit_breaker:
                    if self.circuit_breaker.is_open():
                        logger.warning(
                            "circuit_breaker_open_skipping_primary",
                            component=self.component_name,
                        )
                        continue  # Skip to fallback

                # Execute strategy
                if asyncio.iscoroutinefunction(strategy):
                    result = await strategy(*args, **kwargs)
                else:
                    result = strategy(*args, **kwargs)
                    # If the callable returned a coroutine (e.g., lambda: async_func()),
                    # we need to await it to avoid "coroutine never awaited" warning
                    if asyncio.iscoroutine(result):
                        result = await result

                # Track success
                FALLBACK_COUNTER.labels(
                    component=self.component_name, level=i, success="true"
                ).inc()

                # Log fallback usage
                if i > 0:
                    logger.info(
                        "fallback_strategy_succeeded",
                        component=self.component_name,
                        level=i,
                        strategy_name=strategy.__name__,
                    )

                return result

            except Exception as e:
                last_error = e

                # Track failure
                FALLBACK_COUNTER.labels(
                    component=self.component_name, level=i, success="false"
                ).inc()

                # Log failure
                logger.warning(
                    "fallback_strategy_failed",
                    component=self.component_name,
                    level=i,
                    strategy_name=strategy.__name__,
                    error_type=type(e).__name__,
                    error_msg=str(e),
                    is_last=(i == len(self.strategies) - 1),
                )

                # Continue to next strategy (unless last)
                if i == len(self.strategies) - 1:
                    break

        # All strategies failed
        logger.error(
            "all_fallback_strategies_failed",
            component=self.component_name,
            total_strategies=len(self.strategies),
            last_error=str(last_error),
        )

        raise Exception(
            f"All {len(self.strategies)} fallback strategies failed for '{self.component_name}'. "
            f"Last error: {last_error}"
        ) from last_error
