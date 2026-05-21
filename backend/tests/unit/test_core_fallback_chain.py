"""
Unit tests for FallbackChain pattern.
Tests hierarchical fallback execution, metrics, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.core.infrastructure.fallback_chain import FallbackChain


class TestFallbackChain:
    """Test FallbackChain functionality."""

    @pytest.mark.asyncio
    async def test_primary_strategy_succeeds(self):
        """Test that primary strategy executes successfully."""

        async def primary():
            return "success"

        async def fallback():
            return "fallback"

        chain = FallbackChain([primary, fallback], component_name="test")
        result = await chain.execute()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_fallback_to_secondary(self):
        """Test fallback when primary fails."""

        async def primary():
            raise ValueError("Primary failed")

        async def secondary():
            return "secondary_success"

        chain = FallbackChain([primary, secondary], component_name="test")
        result = await chain.execute()

        assert result == "secondary_success"

    @pytest.mark.asyncio
    async def test_all_strategies_fail(self):
        """Test exception when all strategies fail."""

        async def strategy1():
            raise ValueError("Strategy 1 failed")

        async def strategy2():
            raise RuntimeError("Strategy 2 failed")

        chain = FallbackChain([strategy1, strategy2], component_name="test")

        with pytest.raises(Exception) as exc_info:
            await chain.execute()

        assert "All 2 fallback strategies failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_strategies_with_arguments(self):
        """Test strategies receiving arguments."""

        async def primary(x, y):
            return x + y

        async def fallback(x, y):
            return x * y

        chain = FallbackChain([primary, fallback], component_name="test")
        result = await chain.execute(5, 3)

        assert result == 8

    @pytest.mark.asyncio
    async def test_synchronous_strategy(self):
        """Test that synchronous strategies also work."""

        def sync_strategy():
            return "sync_result"

        chain = FallbackChain([sync_strategy], component_name="test")
        result = await chain.execute()

        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_primary(self):
        """Test circuit breaker integration skips primary when open."""

        # Mock circuit breaker
        cb_mock = Mock()
        cb_mock.is_open.return_value = True

        async def primary():
            raise AssertionError("Primary should be skipped")

        async def fallback():
            return "fallback_used"

        chain = FallbackChain([primary, fallback], component_name="test", circuit_breaker=cb_mock)
        result = await chain.execute()

        assert result == "fallback_used"
        cb_mock.is_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that metrics are incremented correctly."""

        with patch("app.core.infrastructure.fallback_chain.FALLBACK_COUNTER") as mock_counter:

            async def primary():
                raise ValueError("Fail")

            async def secondary():
                return "ok"

            chain = FallbackChain([primary, secondary], component_name="test_comp")
            await chain.execute()

            # Verify metrics were called
            assert mock_counter.labels.call_count >= 2  # At least one failure + one success

    def test_empty_strategies_raises(self):
        """Test that empty strategy list raises ValueError."""

        with pytest.raises(ValueError, match="At least one strategy is required"):
            FallbackChain([], component_name="test")

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self):
        """Test recovery after multiple failures."""

        call_count = 0

        async def flaky_strategy():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError(f"Failure {call_count}")
            return "finally_succeeded"

        async def fallback1():
            raise ValueError("Fallback 1 failed")

        async def fallback2():
            raise ValueError("Fallback 2 failed")

        async def final_fallback():
            return "final_fallback_ok"

        chain = FallbackChain(
            [flaky_strategy, fallback1, fallback2, final_fallback], component_name="test"
        )
        result = await chain.execute()

        # Flaky strategy should never succeed (fails on first execution)
        # So final fallback should be used
        assert result == "final_fallback_ok"
