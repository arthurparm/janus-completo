
import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from app.core.infrastructure.message_broker import MessageBroker
from app.core.infrastructure.resilience import CircuitOpenError
from app.core.llm.client import LLMClient
from app.core.llm.types import ModelRole

# Imports from App (using paths assuming running from root)
from app.core.memory.memory_core import MemoryCore


@dataclass
class ChaosConfig:
    """Configuration for injecting chaos into dependencies."""
    latency_ms: int = 0
    latency_jitter_ms: int = 0
    error_rate: float = 0.0  # 0.0 to 1.0
    error_type: Optional[Exception] = None
    circuit_breaker_state: str = "CLOSED"  # CLOSED, OPEN

    def should_fail(self) -> bool:
        return self.error_rate > 0 and random.random() < self.error_rate

    async def simulate_latency(self):
        if self.latency_ms > 0:
            delay = self.latency_ms
            if self.latency_jitter_ms > 0:
                delay += random.uniform(-self.latency_jitter_ms, self.latency_jitter_ms)
            delay = max(0, delay)
            await asyncio.sleep(delay / 1000.0)

class MockQdrantClient:
    def __init__(self, config: ChaosConfig):
        self.config = config
        self.uploaded_points = []

    async def search(self, *args, **kwargs):
        await self.config.simulate_latency()
        if self.config.should_fail():
            raise self.config.error_type or Exception("Qdrant Chaos Error")
        # Return empty list or minimal structure to pass validation
        return []

    async def upsert(self, collection_name: str, points: List[Any], **kwargs):
        await self.config.simulate_latency()
        if self.config.should_fail():
            raise self.config.error_type or Exception("Qdrant Chaos Error")
        self.uploaded_points.extend(points)
        return True

    async def retrieve(self, *args, **kwargs):
        await self.config.simulate_latency()
        if self.config.should_fail():
            raise self.config.error_type or Exception("Qdrant Chaos Error")
        return []

    async def get_collection(self, *args, **kwargs):
         # Used for health check
        await self.config.simulate_latency()
        if self.config.should_fail():
             raise self.config.error_type or Exception("Qdrant Chaos Error")
        return True

    async def scroll(self, collection_name: str, scroll_filter: Any = None, limit: int = 10, with_payload: bool = True, **kwargs):
        """Simulates Qdrant scroll method."""
        await self.config.simulate_latency()
        if self.config.should_fail():
             raise self.config.error_type or Exception("Qdrant Chaos Error")

        # Return a tuple (points, next_page_offset)
        # For now, return empty list and None (no next page)
        return [], None

class MockCircuitBreaker:
    def __init__(self, config: ChaosConfig):
        self.config = config
        self.calls = 0

    def is_open(self) -> bool:
        return self.config.circuit_breaker_state == "OPEN"

    def call(self, func, *args, **kwargs):
        if self.is_open():
            raise CircuitOpenError("Chaos Circuit Open")
        self.calls += 1
        return func(*args, **kwargs)

    async def call_async(self, coro_func, *args, **kwargs):
        if self.is_open():
            raise CircuitOpenError("Chaos Circuit Open")
        self.calls += 1
        return await coro_func()

    # Simulate decorator
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def update_params(self, **kwargs):
        pass

    def get_health_status(self):
        return {"metrics": {"error_rate": 0.0}}

class MockLLMBase:
    def __init__(self, config: ChaosConfig):
        self.config = config

    def invoke(self, prompt: str):
         # Simulate sync latency (time.sleep) or just skip since resilient handles async mostly?
         # But invoke is sync.
        if self.config.latency_ms > 0:
            time.sleep(self.config.latency_ms / 1000.0)

        if self.config.should_fail():
            raise self.config.error_type or Exception("LLM Chaos Error")

        return MagicMock(content="Chaos LLM Response")

class MockConnectionFactory:
    def __init__(self, config: ChaosConfig):
        self.config = config

    async def __call__(self, *args, **kwargs):
        await self.config.simulate_latency()
        if self.config.should_fail():
             raise self.config.error_type or Exception("Broker Connection Chaos Error")

        # Return a Mock Connection
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        mock_conn.close = AsyncMock()
        mock_conn.channel = MagicMock()

        mock_channel = AsyncMock()
        mock_conn.channel.return_value.__aenter__.return_value = mock_channel

        return mock_conn

class ChaosHarness:
    """
    Factory for instantiating Core components with predictable Chaos settings.
    """

    @staticmethod
    def create_memory_core(config: ChaosConfig, settings_override: Dict[str, Any] = None) -> MemoryCore:
        """Creates a MemoryCore attached to a Mock Qdrant/CB controlled by config."""

        # Mocks
        mock_client = MockQdrantClient(config)
        mock_cb = MockCircuitBreaker(config)

        # Settings
        class MockSettings:
             # Add defaults required by MemoryCore
             MEMORY_VECTOR_SIZE = 1536
             QDRANT_HOST = "mock"
             QDRANT_PORT = 6333
             pass

        s = MockSettings()
        if settings_override:
            for k, v in settings_override.items():
                setattr(s, k, v)

        # Instantiate
        memory = MemoryCore(
            client=mock_client,
            circuit_breaker=mock_cb,
            config=s
        )
        # Force cache/internals init if needed
        memory._cb = mock_cb
        # (Already set in __init__ but to be safe)

        return memory

    @staticmethod
    def create_llm_client(config: ChaosConfig, settings_override: Dict[str, Any] = None) -> LLMClient:

        base = MockLLMBase(config)
        mock_cb = MockCircuitBreaker(config)

        class MockSettings:
            LLM_MAX_PROMPT_LENGTH = 1000
            LLM_DEFAULT_TIMEOUT_SECONDS = 30
            LLM_RETRY_MAX_ATTEMPTS = 3
            LLM_RETRY_INITIAL_BACKOFF_SECONDS = 0.1
            LLM_RETRY_MAX_BACKOFF_SECONDS = 1.0
            IDENTITY_ENFORCEMENT_ENABLED = False

        s = MockSettings()
        if settings_override:
            for k, v in settings_override.items():
                setattr(s, k, v)

        client = LLMClient(
            base=base,
            provider="chaos_provider",
            model="chaos_model",
            role=ModelRole.ORCHESTRATOR,
            cache_key="chaos",
            circuit_breaker=mock_cb,
            config=s
        )

        return client

    @staticmethod
    def create_message_broker(config: ChaosConfig, settings_override: Dict[str, Any] = None) -> MessageBroker:
        mock_factory = MockConnectionFactory(config)

        class MockSettings:
             RABBITMQ_USER = "chaos"
             RABBITMQ_PASSWORD = "chaos"
             RABBITMQ_HOST = "chaos_host"
             RABBITMQ_PORT = 5672
             RABBITMQ_MANAGEMENT_PORT = 15672
             RABBITMQ_QUEUE_CONFIG = {}
             BROKER_USE_MSGPACK = True

        s = MockSettings()
        if settings_override:
            for k, v in settings_override.items():
                setattr(s, k, v)

        return MessageBroker(config=s, connection_factory=mock_factory)

# Demonstration / Verification script
async def run_demo():
    print("--- Running Chaos Harness Demo ---")

    # Scenario 1: High Latency Memory
    print("\nScenario 1: High Latency (500ms) in Memory Upsert")
    cfg = ChaosConfig(latency_ms=500, error_rate=0.0)
    memory = ChaosHarness.create_memory_core(cfg)

    start = time.time()
    try:
        from app.models.schemas import Experience
        exp = Experience(content="Test", type="episodic")
        await memory.amemorize(exp)
        elapsed = time.time() - start
        print(f"Result: Success (Elapsed: {elapsed:.2f}s, Expected: ~0.5s)")
    except Exception as e:
        print(f"Result: Failed ({e})")

    # Scenario 2: LLM Circuit Breaker Open
    print("\nScenario 2: LLM Circuit Breaker OPEN")
    cfg_cb = ChaosConfig(circuit_breaker_state="OPEN")
    llm = ChaosHarness.create_llm_client(cfg_cb)

    try:
        # Use timeout_s=0 to avoid threads hiding exceptions
        llm.send("Hello", timeout_s=0)
        print("Result: Success (Unexpected!)")
    except CircuitOpenError:
        print("Result: Success (Caught CircuitOpenError as expected)")
    except Exception as e:
        print(f"Result: Failed (Caught wrong exception: {type(e).__name__}: {e})")

    # Scenario 3: Broker Connection Failure
    print("\nScenario 3: Broker Connection PROBABILISTIC FAILURE")
    cfg_broker = ChaosConfig(error_rate=1.0, error_type=RuntimeError("Connection Refused"))
    broker = ChaosHarness.create_message_broker(cfg_broker)

    # MessageBroker catches exceptions internally for robustness, but logs errors.
    # For this harness test, let's verify it logged failure or behaves as offline.
    # Note: MessageBroker.connect() swallows exceptions but increments _CONNECTION_ERRORS.
    # We can inspect the logger if patched, or checking internal state.

    await broker.connect()
    if broker._connection is None:
        print("Result: Success (Broker stayed offline due to Chaos)")
    else:
        print("Result: Failed (Broker connected despite Chaos)")

if __name__ == "__main__":
    asyncio.run(run_demo())
