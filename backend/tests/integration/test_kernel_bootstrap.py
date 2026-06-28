import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def _kernel_module():
    """Lazy import of kernel module to avoid import-time cascading failures."""
    from app.core.kernel import Kernel, KernelError, KernelState
    return Kernel, KernelError, KernelState


class TestKernelBootstrap:
    """Integration tests for Kernel bootstrap lifecycle."""

    @pytest.fixture(autouse=True)
    def reset_kernel(self, _kernel_module):
        Kernel, _, _ = _kernel_module
        Kernel.reset_instance()
        yield
        Kernel.reset_instance()

    @pytest.fixture
    def kernel(self, _kernel_module):
        Kernel, _, _ = _kernel_module
        return Kernel.get_instance()

    def _setup_redis_mock(self):
        redis_instance = MagicMock()
        redis_instance.initialize = AsyncMock()
        return patch(
            "app.core.infrastructure.redis_manager.RedisManager.get_instance",
            return_value=redis_instance,
        )

    def _common_success_patches(self):
        return [
            patch("app.core.kernel.setup_logging"),
            patch("app.core.kernel.db.create_tables", AsyncMock()),
            patch(
                "app.services.db_migration_service.db_migration_service.migrate_schema",
                MagicMock(),
            ),
            patch("app.core.kernel.initialize_graph_db", AsyncMock()),
            patch("app.core.kernel.initialize_memory_db", AsyncMock()),
            patch("app.core.kernel.initialize_broker", AsyncMock()),
            patch("app.core.kernel.get_graph_db", AsyncMock(return_value=MagicMock())),
            patch("app.core.kernel.get_memory_db", AsyncMock(return_value=MagicMock())),
            patch("app.core.kernel.get_broker", AsyncMock(return_value=MagicMock())),
            patch("app.core.kernel.get_agent_manager", MagicMock(return_value=MagicMock())),
        ]

    @pytest.mark.asyncio
    async def test_kernel_startup_healthy(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        redis_patcher = self._setup_redis_mock()
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(redis_patcher)

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.HEALTHY
        assert kernel.degraded_dependencies == {}

    @pytest.mark.asyncio
    async def test_kernel_startup_neo4j_fails(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        redis_patcher = self._setup_redis_mock()
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(redis_patcher)
            stack.enter_context(
                patch(
                    "app.core.kernel.initialize_graph_db",
                    AsyncMock(side_effect=ConnectionError("Neo4j unavailable")),
                )
            )

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.DEGRADED
        assert "graph_db" in kernel.degraded_dependencies

    @pytest.mark.asyncio
    async def test_kernel_startup_qdrant_fails(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        redis_patcher = self._setup_redis_mock()
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(redis_patcher)
            stack.enter_context(
                patch(
                    "app.core.kernel.initialize_memory_db",
                    AsyncMock(side_effect=ConnectionError("Qdrant unavailable")),
                )
            )

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.DEGRADED
        assert "memory_db" in kernel.degraded_dependencies

    @pytest.mark.asyncio
    async def test_kernel_startup_rabbitmq_fails(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        redis_patcher = self._setup_redis_mock()
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(redis_patcher)
            stack.enter_context(
                patch(
                    "app.core.kernel.initialize_broker",
                    AsyncMock(side_effect=ConnectionError("RabbitMQ unavailable")),
                )
            )

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.DEGRADED
        assert "broker" in kernel.degraded_dependencies

    @pytest.mark.asyncio
    async def test_kernel_startup_redis_fails(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        redis_instance = MagicMock()
        redis_instance.initialize = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "app.core.infrastructure.redis_manager.RedisManager.get_instance",
                    return_value=redis_instance,
                )
            )

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.DEGRADED
        assert "redis" in kernel.degraded_dependencies

    @pytest.mark.asyncio
    async def test_kernel_startup_postgres_fails(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        from sqlalchemy.exc import OperationalError

        redis_patcher = self._setup_redis_mock()
        with contextlib.ExitStack() as stack:
            for p in self._common_success_patches():
                stack.enter_context(p)
            stack.enter_context(redis_patcher)
            stack.enter_context(
                patch(
                    "app.core.kernel.db.create_tables",
                    AsyncMock(side_effect=OperationalError("connection refused", None, None)),
                )
            )

            await kernel.startup(
                init_infrastructure=True,
                init_mas_actors=False,
                build_dependency_graph=False,
                register_tools=False,
                start_background_processes=False,
                warmup_llms=False,
                init_senses=False,
            )

        assert kernel.state == KernelState.HEALTHY

    @pytest.mark.asyncio
    async def test_kernel_shutdown_resilient(self, kernel, _kernel_module):
        _, _, KernelState = _kernel_module
        kernel.degraded_dependencies = {"graph_db": "test error"}
        kernel._state = KernelState.DEGRADED

        await kernel.shutdown()

        assert kernel.state == KernelState.DEGRADED
