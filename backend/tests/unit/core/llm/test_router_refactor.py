from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.router import get_llm
from app.core.llm.types import ModelPriority, ModelRole, ProviderPricing


@pytest.mark.asyncio
async def test_get_llm_local_only_mantem_ollama_como_caminho_primario():
    mock_llm = MagicMock(name="ollama_llm")

    with (
        patch("app.core.llm.router._get_from_pool", return_value=None),
        patch("app.core.llm.router.create_ollama_llm", return_value=mock_llm),
        patch("app.core.llm.router._health_check_ollama", return_value=True),
        patch.object(
            __import__("app.core.llm.router", fromlist=["settings"]).settings,
            "OLLAMA_ORCHESTRATOR_MODEL",
            "llama3",
        ),
    ):
        llm = await get_llm(
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.LOCAL_ONLY,
        )

    assert llm is mock_llm


@pytest.mark.asyncio
async def test_get_llm_fast_and_cheap_escolhe_candidato_mais_barato_disponivel():
    gemini_llm = MagicMock(name="gemini_llm")
    openai_llm = MagicMock(name="openai_llm")
    mock_settings = __import__("app.core.llm.router", fromlist=["settings"]).settings

    with (
        patch("app.core.llm.router._get_from_pool", return_value=None),
        patch("app.core.llm.router._add_to_pool"),
        patch("app.core.llm.router._validate_deepseek_key", return_value=False),
        patch("app.core.llm.router._validate_xai_key", return_value=False),
        patch("app.core.llm.router._validate_gemini_key", return_value=True),
        patch("app.core.llm.router._validate_openai_key", return_value=True),
        patch("app.core.llm.router._circuit_closed", return_value=True),
        patch("app.core.llm.router._budget_allows", AsyncMock(return_value=True)),
        patch("app.core.llm.router.ChatGoogleGenerativeAI", return_value=gemini_llm),
        patch("app.core.llm.router._create_openai_model", return_value=openai_llm),
        patch("app.core.llm.router._get_model_pricing") as mock_pricing,
        patch.object(mock_settings, "GEMINI_MODELS", ["gemini-2.5-flash"]),
        patch.object(mock_settings, "GEMINI_MODEL_NAME", "gemini-2.5-flash"),
        patch.object(mock_settings, "OPENAI_MODELS", ["gpt-4o"]),
        patch.object(mock_settings, "OPENAI_MODEL_NAME", "gpt-4o"),
        patch.object(mock_settings, "LLM_CLOUD_MODEL_CANDIDATES", {}),
        patch.object(mock_settings, "LLM_ECONOMY_POLICY", "balanced"),
        patch.object(mock_settings, "LLM_EXPLORATION_PERCENT", 0.0),
        patch.object(mock_settings, "LLM_MAX_COST_PER_REQUEST_USD", {"orchestrator": 1.0}),
        patch.object(mock_settings, "LLM_EXPECTED_KTOKENS_BY_ROLE", {"orchestrator": 1.0}),
    ):
        mock_pricing.side_effect = lambda provider, model: (
            ProviderPricing(1.0, 1.0)
            if provider == "google_gemini"
            else ProviderPricing(10.0, 10.0)
        )

        llm = await get_llm(
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )

    assert llm is gemini_llm
