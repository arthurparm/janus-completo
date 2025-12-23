
import pytest
from unittest.mock import MagicMock, patch
from app.core.llm.router import get_llm
from app.core.llm.types import ModelRole, ModelPriority, ProviderPricing
from app.core.llm.pricing import _provider_budgets_usd, _provider_spend_usd

@pytest.fixture
def mock_settings():
    with patch("app.core.llm.router.settings") as mock:
        mock.LLM_POOL_TTL_SECONDS = 3600
        mock.LLM_POOL_MAX_SIZE = 4
        # Defaults
        mock.OLLAMA_HOST = "http://localhost:11434"
        mock.OLLAMA_ORCHESTRATOR_MODEL = "llama3"
        yield mock

@pytest.fixture
def mock_pool():
    with patch("app.core.llm.router._get_from_pool", return_value=None):
        with patch("app.core.llm.router._add_to_pool"):
             yield

@pytest.fixture
def mock_pricing():
    # Reset budgets for test
    with patch.dict(_provider_budgets_usd, {"openai": 100.0, "google_gemini": 100.0, "ollama": 0.0}, clear=True):
        with patch.dict(_provider_spend_usd, {"openai": 0.0, "google_gemini": 0.0, "ollama": 0.0}, clear=True):
            yield

def test_get_llm_local_only(mock_settings, mock_pool):
    with patch("app.core.llm.router.ChatOllama") as MockOllama:
        mock_instance = MagicMock()
        MockOllama.return_value = mock_instance
        # Mock health check to pass
        with patch("app.core.llm.router._health_check_ollama", return_value=True):
            llm = get_llm(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.LOCAL_ONLY)
            assert llm == mock_instance
            MockOllama.assert_called()
            # Verify model name used
            args, kwargs = MockOllama.call_args
            assert kwargs['model'] == "llama3"

def test_get_llm_fast_and_cheap_selects_cheapest(mock_settings, mock_pool, mock_pricing):
    # Mock cloud catalog to have valid providers
    with patch("app.core.llm.router._validate_openai_key", return_value=True), \
         patch("app.core.llm.router._validate_gemini_key", return_value=True), \
         patch("app.core.llm.router._circuit_closed", return_value=True):
        
        # Mock candidates and pricing
        # We need to mock how router gets candidates. It iterates cloud_catalog.
        # We also need to mock _get_model_pricing
        
        with patch("app.core.llm.router._get_model_pricing") as mock_get_pricing:
            # OpenAI expensive
            # Gemini cheap
            def side_effect(provider, model):
                if provider == "openai":
                    return ProviderPricing(10.0, 30.0) # $40 total
                return ProviderPricing(1.0, 1.0) # $2 total
            
            mock_get_pricing.side_effect = side_effect
            
            # Mock ChatOpenAI and ChatGoogleGenerativeAI factories
            with patch("app.core.llm.router.ChatOpenAI") as MockOpenAI, \
                 patch("app.core.llm.router.ChatGoogleGenerativeAI") as MockGemini:
                
                MockOpenAI.return_value = MagicMock(name="openai_llm")
                MockGemini.return_value = MagicMock(name="gemini_llm")
                
                # Mock settings for models
                mock_settings.GEMINI_MODELS = ["gemini-pro"]
                mock_settings.GEMINI_MODEL_NAME = "gemini-pro"
                mock_settings.OPENAI_MODELS = ["gpt-4"]
                mock_settings.OPENAI_MODEL_NAME = "gpt-4"
                
                # Execute
                llm = get_llm(priority=ModelPriority.FAST_AND_CHEAP)
                
                # Should select Gemini because it's cheaper (score logic favors lower cost in balanced/strict mode)
                # Ensure we didn't pick OpenAI
                assert llm == MockGemini.return_value
