from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.llm import response_cache
from app.core.llm.client import LLMClient, get_llm_client
from app.core.llm.types import ModelRole, ProviderPricing


class _MockSettings:
    LLM_MAX_PROMPT_LENGTH = 1000
    LLM_MAX_COST_PER_REQUEST_USD = {}
    LLM_MAX_GENERATION_TOKENS_CAP = 256
    LLM_MIN_GENERATION_TOKENS = 16
    LLM_DEFAULT_TIMEOUT_SECONDS = 30
    LLM_RETRY_MAX_ATTEMPTS = 1
    LLM_RETRY_INITIAL_BACKOFF_SECONDS = 0.01
    LLM_RETRY_MAX_BACKOFF_SECONDS = 0.01
    LLM_FALLBACK_ENABLED = False
    OLLAMA_ENABLED = False
    IDENTITY_ENFORCEMENT_ENABLED = False
    AGENT_IDENTITY_NAME = "Janus"
    APP_NAME = "Janus"
    OLLAMA_HOST = "http://localhost:11434"
    OLLAMA_ORCHESTRATOR_MODEL = "gpt-oss:20b"
    OLLAMA_NUM_CTX = None
    OLLAMA_NUM_THREAD = None
    OLLAMA_NUM_BATCH = None
    OLLAMA_GPU_LAYERS = None
    OLLAMA_KEEP_ALIVE = None


@pytest.fixture(autouse=True)
def clean_cache():
    response_cache.invalidate()
    yield
    response_cache.invalidate()


def _build_client(mock_base: MagicMock, *, response_cache_enabled: bool = True) -> LLMClient:
    return LLMClient(
        base=mock_base,
        provider="mock",
        model="mock-model",
        role=ModelRole.ORCHESTRATOR,
        cache_key="orchestrator_fast_and_cheap",
        config=_MockSettings(),
        response_cache_enabled=response_cache_enabled,
    )


@pytest.mark.asyncio
async def test_asend_prefere_ainvoke_e_reutiliza_cache():
    mock_base = MagicMock()
    mock_base.ainvoke = AsyncMock(return_value=SimpleNamespace(content="resposta async"))
    mock_base.invoke = MagicMock(return_value=SimpleNamespace(content="resposta sync"))
    client = _build_client(mock_base)

    rate_limiter = MagicMock()
    with (
        patch("app.core.llm.client._get_model_pricing", return_value=ProviderPricing(0.0, 0.0)),
        patch("app.core.llm.client._budget_remaining", AsyncMock(return_value=float("inf"))),
        patch(
            "app.core.llm.client._tenant_budget_remaining",
            AsyncMock(return_value=float("inf")),
        ),
        patch(
            "app.core.llm.client._objective_budget_remaining",
            AsyncMock(return_value=float("inf")),
        ),
        patch("app.core.llm.client.get_timeout_recommendation", return_value=30.0),
        patch("app.core.llm.client.get_rate_limiter", return_value=rate_limiter),
    ):
        first = await client.asend("ping")
        second = await client.asend("ping")

    assert first == "resposta async"
    assert second == "resposta async"
    mock_base.ainvoke.assert_awaited_once()
    mock_base.invoke.assert_not_called()
    rate_limiter.register_usage.assert_called_once()


@pytest.mark.asyncio
async def test_strict_client_bypasses_read_and_write_response_cache():
    response_cache.put(
        prompt="ping",
        role="orchestrator",
        priority="fast_and_cheap",
        response="wrong provider cache",
        provider="openai",
        model="gpt-5.6-luna",
    )
    mock_base = MagicMock()
    mock_base.ainvoke = AsyncMock(return_value=SimpleNamespace(content="strict provider response"))
    client = _build_client(mock_base, response_cache_enabled=False)

    with (
        patch("app.core.llm.client._get_model_pricing", return_value=ProviderPricing(0.0, 0.0)),
        patch("app.core.llm.client._budget_remaining", AsyncMock(return_value=float("inf"))),
        patch(
            "app.core.llm.client._tenant_budget_remaining",
            AsyncMock(return_value=float("inf")),
        ),
        patch(
            "app.core.llm.client._objective_budget_remaining",
            AsyncMock(return_value=float("inf")),
        ),
        patch("app.core.llm.client.get_timeout_recommendation", return_value=30.0),
        patch("app.core.llm.client.get_rate_limiter", return_value=MagicMock()),
    ):
        result = await client.asend("ping")

    assert result == "strict provider response"
    mock_base.ainvoke.assert_awaited_once()
    cached = response_cache.get("ping", "orchestrator", "fast_and_cheap")
    assert cached is not None
    assert cached["response"] == "wrong provider cache"


@pytest.mark.asyncio
async def test_get_llm_client_disables_cache_for_strict_provider():
    mock_base = MagicMock()
    with (
        patch("app.core.llm.client.get_llm", AsyncMock(return_value=mock_base)),
        patch("app.core.llm.client._infer_provider", return_value="xai"),
        patch("app.core.llm.client._infer_model_name", return_value="grok-4.5"),
    ):
        client = await get_llm_client(config={"strict_provider": True})

    assert client.response_cache_enabled is False

def test_llm_client_nao_exporta_mais_send():
    client = _build_client(MagicMock())
    assert not hasattr(client, "send")


@pytest.mark.asyncio
async def test_cloud_only_runtime_bloqueia_fallback_ollama():
    client = _build_client(MagicMock())

    with pytest.raises(RuntimeError, match="disabled by runtime policy"):
        await client._invoke_with_fallback("ping")
