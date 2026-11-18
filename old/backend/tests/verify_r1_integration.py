import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.llm.types import ModelRole, ModelPriority
from app.core.llm.router import get_llm

class TestDeepSeekV4Integration(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.llm.router.settings")
    @patch("app.core.llm.router._validate_deepseek_key")
    @patch("app.core.llm.router._budget_allows")
    @patch("app.core.llm.router._circuit_closed")
    @patch("app.core.llm.router.get_rate_limiter")
    async def test_reasoner_selection(self, mock_limiter, mock_circuit, mock_budget, mock_validate_key, mock_settings):
        # Setup Mocks
        mock_settings.LLM_CLOUD_MODEL_CANDIDATES = {"reasoner": ["deepseek:deepseek-v4-pro"]}
        mock_settings.DEEPSEEK_API_KEY = MagicMock()
        mock_settings.DEEPSEEK_BASE_URL = "http://mock"
        mock_settings.DEEPSEEK_MODEL_NAME = "deepseek-v4-flash"
        mock_settings.DEEPSEEK_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]
        
        # Mock Default/Safe settings
        mock_settings.LLM_MAX_COST_PER_REQUEST_USD = {}
        mock_settings.LLM_EXPECTED_KTOKENS_BY_ROLE = {}
        mock_settings.LLM_ECONOMY_POLICY = "balanced"
        
        # Mock validation/availability
        mock_validate_key.return_value = True
        mock_budget.return_value = True
        mock_circuit.return_value = True
        
        limiter_instance = MagicMock()
        limiter_instance.is_available.return_value = True
        mock_limiter.return_value = limiter_instance

        # Execute
        print("\n[TEST] Requesting LLM for REASONER role...")
        llm = await get_llm(role=ModelRole.REASONER, priority=ModelPriority.HIGH_QUALITY)
        
        # Verify
        print(f"[RESULT] Selected LLM: {llm}")
        
        # Check if it selected DeepSeek V4 Pro
        # Note: router returns a ChatOpenAI instance
        self.assertEqual(llm.model_name, "deepseek-v4-pro")
        self.assertEqual(llm.openai_api_base, "http://mock")
        
        print("[SUCCESS] deepseek-v4-pro selected")

if __name__ == "__main__":
    unittest.main()
