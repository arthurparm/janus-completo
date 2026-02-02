from unittest.mock import MagicMock

import pytest

from app.core.llm import response_cache
from app.core.llm.client import LLMClient
from app.core.llm.types import ModelRole


@pytest.fixture(autouse=True)
def clean_cache():
    response_cache.invalidate()
    yield
    response_cache.invalidate()


def test_llm_client_cache_integration():
    # Mock Base LLM
    mock_base = MagicMock()
    mock_base.invoke.return_value.content = "Cached Response"

    # Init Client
    client = LLMClient(
        base=mock_base,
        provider="mock",
        model="mock-gpt",
        role=ModelRole.ORCHESTRATOR,
        cache_key="orch_high",
    )

    prompt = "What is 2+2?"

    # First Call - Should hit invoke
    print("\n[TEST] 1st Call")
    res1 = client.send(prompt)
    assert res1 == "Cached Response"
    assert mock_base.invoke.call_count == 1

    # Second Call - Should hit cache (invoke count remains 1)
    print("\n[TEST] 2nd Call")
    res2 = client.send(prompt)
    assert res2 == "Cached Response"
    assert mock_base.invoke.call_count == 1  # Still 1!

    print("[SUCCESS] Cache Hit Verified!")


if __name__ == "__main__":
    test_llm_client_cache_integration()
