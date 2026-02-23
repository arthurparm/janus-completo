import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.llm.types import ModelRole, ModelPriority
from app.core.llm.router import get_llm

class TestR1Integration(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.llm.router.settings")
    @patch("app.core.llm.router._validate_deepseek_key")
    @patch("app.core.llm.router._budget_allows")
    @patch("app.core.llm.router._circuit_closed")
    @patch("app.core.llm.router.get_rate_limiter")
    async def test_reasoner_selection(self, mock_limiter, mock_circuit, mock_budget, mock_validate_key, mock_settings):
        # Setup Mocks
        mock_settings.LLM_CLOUD_MODEL_CANDIDATES = {"reasoner": ["deepseek:deepseek-reasoner"]}
        mock_settings.DEEPSEEK_API_KEY = MagicMock()
        mock_settings.DEEPSEEK_BASE_URL = "http://mock"
        mock_settings.DEEPSEEK_MODEL_NAME = "deepseek-chat"
        mock_settings.DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-reasoner"]
        
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
        
        # Check if it selected DeepSeek Reasoner
        # Note: router returns a ChatOpenAI instance
        self.assertEqual(llm.model_name, "deepseek-reasoner")
        self.assertEqual(llm.openai_api_base, "http://mock")
        
        # Validate output limit for R1 in a version-compatible way.
        max_tokens = getattr(llm, "max_tokens", None)
        if max_tokens is None:
            max_tokens = (getattr(llm, "model_kwargs", {}) or {}).get("max_tokens")
        self.assertEqual(max_tokens, 8000)
        print("[SUCCESS] deepseek-reasoner selected with max_tokens=8000")

if __name__ == "__main__":
    unittest.main()
