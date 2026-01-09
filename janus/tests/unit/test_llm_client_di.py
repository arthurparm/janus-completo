from unittest.mock import MagicMock

import pytest

from app.core.llm.client import LLMClient
from app.core.llm.types import ModelRole


@pytest.mark.asyncio
async def test_llm_client_dependency_injection():
    # 1. Mock dependencies
    mock_base = MagicMock()
    def side_effect(*args, **kwargs):
        print(f"DEBUG: invoke called with {args}")
        return MagicMock(content="Mock response")
    mock_base.invoke.side_effect = side_effect

    mock_cb = MagicMock()
    # CircuitBreaker is called as a decorator: cb(func).
    # Must return func (or wrapper) to execute original function.
    mock_cb.side_effect = lambda f: f

    class MockSettings:
        LLM_MAX_PROMPT_LENGTH = 1000
        LLM_MAX_COST_PER_REQUEST_USD = {}
        LLM_MAX_GENERATION_TOKENS_CAP = 100
        LLM_MIN_GENERATION_TOKENS = 10
        IDENTITY_ENFORCEMENT_ENABLED = False
        AGENT_IDENTITY_NAME = "Janus"
        APP_NAME = "Janus"
        LLM_DEFAULT_TIMEOUT_SECONDS = 30
        LLM_RETRY_MAX_ATTEMPTS = 1
        LLM_RETRY_INITIAL_BACKOFF_SECONDS = 0.1
        LLM_RETRY_MAX_BACKOFF_SECONDS = 0.5

    mock_settings = MockSettings()

    # 2. Instantiate LLMClient with mocks (DI)
    client = LLMClient(
        base=mock_base,
        provider="mock_provider",
        model="mock_model",
        role=ModelRole.ORCHESTRATOR,
        cache_key="mock_key",
        circuit_breaker=mock_cb,
        config=mock_settings
    )

    # 3. Verify internal state
    assert client.base is mock_base
    assert client.circuit_breaker is mock_cb
    assert client.settings is mock_settings

    # 4. Invoke send and verify dependencies are used
    # Use timeout_s=0 to avoid ThreadPoolExecutor and run synchronously for easier mock verification
    response = client.send("Hello world", timeout_s=0)

    # Assert base model was called
    mock_base.invoke.assert_called_once()

    # Assert settings were accessed (implicit by execution success)
    assert response == "Mock response"

    # Assert Circuit Breaker was updated/used
    # The client calls circuit_breaker.update_params inside send
    mock_cb.update_params.assert_called()

    print("✅ Dependency Injection Test Passed: LLMClient used injected dependencies!")

if __name__ == "__main__":
    test_llm_client_dependency_injection()
