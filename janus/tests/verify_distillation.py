import json
import os
import sys
import tempfile
import unittest

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.knowledge.distillation_service import DistillationService
from app.models.schemas import TaskState, TaskStateEvent


class TestDistillationPipeline(unittest.TestCase):
    def setUp(self):
        # Create a temp file for the dataset
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".jsonl")
        self.service = DistillationService(dataset_path=self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_high_quality_task_sanitization(self):
        print(f"\n{'='*50}\nTEST CASE 1: High Quality Task + Sanitization\n{'='*50}")

        # Create a task with reasoning and secrets
        task = TaskState(
            original_goal="Analyze this API key: sk-abcdef1234567890abcdef1234567890abcdef1234567890",
            status="completed",
            data_payload={
                "response": "Here is the result with a Bearer token: Bearer abcdef1234567890abcdef1234567890",
            },
        )
        task.task_id = "task-123"

        # Add a history event with reasoning
        event = TaskStateEvent(
            agent_role="thinker",
            action="thought",
            reasoning="Step 1: Check the key sk-abcdef1234567890abcdef1234567890abcdef1234567890.\nStep 2: It looks valid.\nStep 3: Proceed with caution. This is a very long reasoning trace to ensure it passes the quality filter (> 50 chars heuristic).",
        )
        task.history.append(event)

        print(f"[INPUT] Task ID: {task.task_id}")
        print(f"[INPUT] Reasoning Length: {len(event.reasoning)}")

        # Process
        result = self.service.process_task(task)

        print(f"[ACTION] Processed? {result}")
        self.assertTrue(result)

        # Verify File Content
        with open(self.temp_db_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])

        print("\n[VALIDATION] Checking Sanitization...")
        print(f"[DEBUG] Instruction: {entry['instruction']}")
        print(f"[DEBUG] Output: {entry['output']}")
        print(f"[DEBUG] Reasoning: {entry['reasoning']}")

        # Assert Secrets are Gone
        self.assertNotIn("sk-abcdef", entry["instruction"])
        self.assertIn("[REDACTED_SECRET]", entry["instruction"])

        self.assertNotIn("Bearer abcdef", entry["output"])
        self.assertIn("[REDACTED_SECRET]", entry["output"])

        self.assertNotIn("sk-abcdef", entry["reasoning"])
        self.assertIn("[REDACTED_SECRET]", entry["reasoning"])

        print("[RESULT] ✅ PASSED (Secrets Redacted)")

    def test_low_quality_task_rejection(self):
        print(f"\n{'='*50}\nTEST CASE 2: Low Quality Rejection\n{'='*50}")

        # Task with no reasoning
        task = TaskState(
            original_goal="Simple hello", status="completed", data_payload={"response": "Hello"}
        )

        print("[INPUT] Task without reasoning or short reasoning.")
        result = self.service.process_task(task)
        print(f"[ACTION] Processed? {result}")

        self.assertFalse(result)

        # Task with VERY short reasoning
        task.history.append(TaskStateEvent(action="thought", reasoning="Too short"))
        result = self.service.process_task(task)
        print(f"[ACTION] Processed (Short reasoning)? {result}")
        self.assertFalse(result)

        print("[RESULT] ✅ PASSED (Low quality ignored)")


if __name__ == "__main__":
    unittest.main()
