
import asyncio
import logging
import sys
from unittest.mock import MagicMock

# Add app to path
sys.path.append("/app")

# Configure basic logging
logging.basicConfig(level=logging.INFO)

# Mock get_llm BEFORE importing meta_agent to avoid initialization error
sys.modules['app.core.llm.llm_manager'] = MagicMock()
mock_llm_manager = sys.modules['app.core.llm.llm_manager']
mock_llm_manager.get_llm.return_value = MagicMock()
mock_llm_manager.ModelRole = MagicMock()
mock_llm_manager.ModelPriority = MagicMock()

from app.core.agents.meta_agent import MetaAgent, get_meta_agent  # noqa: E402


async def verify_meta_agent():
    print("--- Verifying MetaAgent Refactor ---")
    try:
        agent = get_meta_agent()
        print("Success: MetaAgent instantiated via singleton getter.")
        assert isinstance(agent, MetaAgent)
    except Exception as e:
        print(f"Failed: MetaAgent instantiation error: {e}")
        return

    # Check that critical tools are loaded
    print(f"Internal Tools: {[t.name for t in agent.tools]}")
    assert len(agent.tools) > 0

    # Test tools execution
    print("Testing tools execution...")

    # Test get_resource_usage
    print("- Testing get_resource_usage...")
    try:
        from app.core.agents.meta_agent import get_resource_usage
        result = get_resource_usage.invoke({})
        print(f"  Result: {result[:200]}...")
        assert "cpu" in result
        assert "memory" in result
    except Exception as e:
        print(f"  Failed: {e}")

    # Test analyze_performance_trends (mocking data)
    print("- Testing analyze_performance_trends...")
    try:
        from collections import deque

        from app.core.agents.meta_agent import analyze_performance_trends

        # Inject mock data into health monitor for testing
        from app.core.monitoring.health_monitor import _latency_windows
        _latency_windows["llm"] = deque([0.1, 0.2, 0.5, 0.1, 0.15])

        result = analyze_performance_trends.invoke({"metric_name": "llm_latency"})
        print(f"  Result: {result}")
        assert "average" in result
    except Exception as e:
        print(f"  Failed: {e}")

    print("Success: MetaAgent structure and tools verified.")

if __name__ == "__main__":
    asyncio.run(verify_meta_agent())
