import os
import sys
import unittest
from unittest.mock import MagicMock

# Ajusta path para rodar dentro do container ou local
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.llm.client import LLMClient


class TestReasoningExtraction(unittest.TestCase):
    def test_extract_reasoning_from_tags(self):
        # Mock Repository
        mock_repo = MagicMock()

        # Instantiate Client
        role_mock = MagicMock()
        role_mock.value = "coder"
        mock_base = MagicMock()
        client = LLMClient(
            base=mock_base,
            provider="ollama",
            model="deepseek-r1",
            role=role_mock,
            cache_key="test_cache",
        )

        # Mock send() to return text with think tags
        client.send = MagicMock(
            return_value="<think>Step 1: Analyze input.\nStep 2: Generate output.</think>\nHere is the result."
        )
        client.provider = "ollama"
        client.model = "deepseek-r1"
        client.role = MagicMock()
        client.role.value = "coder"

        # Execute send_enriched
        result = client.send_enriched("test prompt")

        # Verify reasoning extraction
        print(f"\n{'='*50}\nTEST CASE 1: Reasoning Extraction (DeepSeek/Ollama)\n{'='*50}")
        print("[INPUT] Simulated LLM Response with <think> tags.")
        print("[ACTION] Parsing extracted reasoning...")

        extracted = result.get("reasoning")
        print(f"[DEBUG] Raw Reasoning Content:\n{extracted}")

        self.assertEqual(extracted, "Step 1: Analyze input.\nStep 2: Generate output.")
        print("[VALIDATION] Content matches expected baseline? YES.")

        self.assertIn("Here is the result", result["response"])
        print("[VALIDATION] Response text cleaned/preserved? YES.")
        print("[RESULT] ✅ PASSED")

    def test_no_reasoning_tags(self):
        # Mock Repository
        mock_repo = MagicMock()

        # Instantiate Client
        role_mock = MagicMock()
        role_mock.value = "coder"
        mock_base = MagicMock()
        client = LLMClient(
            base=mock_base, provider="openai", model="gpt-4", role=role_mock, cache_key="test_cache"
        )

        # Mock send() without tags
        client.send = MagicMock(return_value="Just a normal response.")
        client.provider = "openai"
        client.model = "gpt-4"
        client.role = MagicMock()
        client.role.value = "coder"

        # Execute send_enriched
        result = client.send_enriched("test prompt")

        # Verify None
        print(f"\n{'='*50}\nTEST CASE 2: Negative Test (No Tags)\n{'='*50}")
        print("[INPUT] Simulated LLM Response WITHOUT tags (Standard GPT-4o).")
        print("[ACTION] Attempting reasoning extraction...")

        extracted = result.get("reasoning")
        print(f"[DEBUG] Extracted Value: {extracted}")

        self.assertIsNone(extracted)
        print("[VALIDATION] Value is correctly None? YES.")
        print("[RESULT] ✅ PASSED")


if __name__ == "__main__":
    unittest.main()
