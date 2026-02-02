import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Ajusta path para rodar dentro do container ou local
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

# Import functional worker components
from app.core.workers.red_team_agent_worker import process_red_team_task
from app.models.schemas import TaskMessage, TaskState


class TestRedTeamAgent(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.workers.red_team_agent_worker.CollaborationService")
    @patch("app.core.workers.red_team_agent_worker.LLMService")
    @patch("app.core.workers.red_team_agent_worker.get_broker")
    async def test_process_vulnerable_code(self, mock_broker, MockLLMService, MockCollabService):
        # Setup mocks
        mock_llm_instance = MockLLMService.return_value
        mock_collab_instance = MockCollabService.return_value
        mock_collab_instance.pass_task = AsyncMock()

        # Mock LLM response for vulnerability
        mock_llm_instance.invoke_llm.return_value = {
            "response": "VULNERABLE: SQL Injection detected.",
            "reasoning": "Thinking process...",
            "provider": "ollama",
            "model": "qwen2.5-coder",
        }

        # Create TaskMessage with vulnerable code
        state = TaskState(
            task_id="test-task-1",
            goal="Create login function",
            original_goal="Create login function",
            data_payload={
                "code_snippets": {"login.py": "query = 'SELECT * FROM users WHERE user=' + user"},
                "context": "",
            },
        )
        task_msg = TaskMessage(
            task_id="test-task-1",
            task_type="task_state",
            payload={"task_state": state.model_dump()},
            timestamp=1234567890.0,
        )

        # Execute
        await process_red_team_task(task_msg)

        # Retrieve the updated state passed to collab service
        args, _ = mock_collab_instance.pass_task.call_args
        updated_state = args[0]

        # Verify reject called (sent back to coder)
        self.assertEqual(updated_state.next_agent_role, "coder")
        self.assertEqual(updated_state.history[-1].action, "security_audit_failed")
        self.assertIn("SQL Injection", updated_state.history[-1].notes)

    @patch("app.core.workers.red_team_agent_worker.CollaborationService")
    @patch("app.core.workers.red_team_agent_worker.LLMService")
    @patch("app.core.workers.red_team_agent_worker.get_broker")
    async def test_process_safe_code(self, mock_broker, MockLLMService, MockCollabService):
        # Setup mocks
        mock_llm_instance = MockLLMService.return_value
        mock_collab_instance = MockCollabService.return_value
        mock_collab_instance.pass_task = AsyncMock()

        # Mock LLM response for safe code
        mock_llm_instance.invoke_llm.return_value = {
            "response": "SAFE: Code looks good.",
            "reasoning": "Thinking process...",
            "provider": "ollama",
            "model": "qwen2.5-coder",
        }

        # Create TaskMessage with safe code
        state = TaskState(
            task_id="test-task-2",
            goal="Create login function",
            original_goal="Create login function",
            data_payload={
                "code_snippets": {"login.py": "query = 'SELECT * FROM users WHERE user=?'"},
                "context": "",
            },
        )
        task_msg = TaskMessage(
            task_id="test-task-2",
            task_type="task_state",
            payload={"task_state": state.model_dump()},
            timestamp=1234567890.0,
        )

        # Execute
        await process_red_team_task(task_msg)

        # Retrieve the updated state passed to collab service
        args, _ = mock_collab_instance.pass_task.call_args
        updated_state = args[0]

        # Verify approve called (sent to professor)
        self.assertEqual(updated_state.next_agent_role, "professor")
        self.assertEqual(updated_state.history[-1].action, "security_audit_passed")

        # Ensure it wasn't skipped
        self.assertNotIn("Skipped", updated_state.history[-1].notes)
        self.assertIn("SAFE", updated_state.history[-1].notes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
