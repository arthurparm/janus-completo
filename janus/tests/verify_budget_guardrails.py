"""
Verification script for Dynamic Budget Guardrails feature.
"""

import os
import sys
import unittest

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestDynamicBudgetGuardrails(unittest.TestCase):
    def test_guardrail_triggers_at_threshold(self):
        """Test that guardrail triggers when spending >= 90% of budget."""
        print(f"\n{'='*50}\nTEST: Guardrail Triggers at Threshold\n{'='*50}")

        from app.core.llm import pricing

        # Save original state
        original_spend = dict(pricing._provider_spend_usd)
        original_budgets = dict(pricing._provider_budgets_usd)

        try:
            # Set budgets: total = 100
            pricing._provider_budgets_usd["openai"] = 50.0
            pricing._provider_budgets_usd["deepseek"] = 50.0
            pricing._provider_budgets_usd["google_gemini"] = 0.0

            # Set spend to 90% of total (90)
            pricing._provider_spend_usd["openai"] = 45.0
            pricing._provider_spend_usd["deepseek"] = 45.0
            pricing._provider_spend_usd["google_gemini"] = 0.0

            result = pricing.is_total_budget_threshold_exceeded()
            print("Total Budget: $100, Total Spend: $90, Threshold: 90%")
            print(f"Result (should be True): {result}")
            self.assertTrue(result)
            print("✅ Guardrail correctly triggered at 90% threshold.")
        finally:
            # Restore original state
            pricing._provider_spend_usd.update(original_spend)
            pricing._provider_budgets_usd.update(original_budgets)

    def test_guardrail_not_triggers_below_threshold(self):
        """Test that guardrail does NOT trigger when spending < 90% of budget."""
        print(f"\n{'='*50}\nTEST: Guardrail NOT Triggered Below Threshold\n{'='*50}")

        from app.core.llm import pricing

        # Save original state
        original_spend = dict(pricing._provider_spend_usd)
        original_budgets = dict(pricing._provider_budgets_usd)

        try:
            # Set budgets: total = 100
            pricing._provider_budgets_usd["openai"] = 50.0
            pricing._provider_budgets_usd["deepseek"] = 50.0
            pricing._provider_budgets_usd["google_gemini"] = 0.0

            # Set spend to 50% of total (50)
            pricing._provider_spend_usd["openai"] = 25.0
            pricing._provider_spend_usd["deepseek"] = 25.0
            pricing._provider_spend_usd["google_gemini"] = 0.0

            result = pricing.is_total_budget_threshold_exceeded()
            print("Total Budget: $100, Total Spend: $50, Threshold: 90%")
            print(f"Result (should be False): {result}")
            self.assertFalse(result)
            print("✅ Guardrail correctly did NOT trigger below threshold.")
        finally:
            # Restore original state
            pricing._provider_spend_usd.update(original_spend)
            pricing._provider_budgets_usd.update(original_budgets)

    def test_config_exists(self):
        """Test that BUDGET_THRESHOLD_PERCENT config exists."""
        print(f"\n{'='*50}\nTEST: Config Exists\n{'='*50}")

        from app.config import settings

        threshold = getattr(settings, "BUDGET_THRESHOLD_PERCENT", None)
        print(f"BUDGET_THRESHOLD_PERCENT = {threshold}")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold, 0.90)
        print("✅ Config correctly set to 0.90 (90%)")


if __name__ == "__main__":
    unittest.main()
