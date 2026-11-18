
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm import response_cache
from app.core.llm.client import LLMClient
from app.core.llm.types import ModelRole


@pytest.fixture(autouse=True)
def clean_cache():
    response_cache.invalidate()
    yield
    response_cache.invalidate()

@pytest.mark.asyncio
async def test_llm_client_cache_integration():
    # Mock Base LLM
    mock_base = MagicMock()
    mock_base.ainvoke = AsyncMock(return_value=MagicMock(content="Cached Response"))

    # Init Client
    client = LLMClient(
        base=mock_base,
        provider="mock",
        model="mock-gpt",
        role=ModelRole.ORCHESTRATOR,
        cache_key="orch_high"
    )

    prompt = "What is 2+2"

    # First Call - Should hit invoke
    print("\n[TEST] 1st Call")
    res1 = await client.asend(prompt)
    assert res1 == "Cached Response"
    assert mock_base.ainvoke.await_count == 1

    # Second Call - Should hit cache (invoke count remains 1)
    print("\n[TEST] 2nd Call")
    res2 = await client.asend(prompt)
    assert res2 == "Cached Response"
    assert mock_base.ainvoke.await_count == 1 # Still 1!

    print("[SUCCESS] Cache Hit Verified!")

if __name__ == "__main__":
    test_llm_client_cache_integration()
