"""
Teste de verificação para o fluxo do Thinker Agent.
Simula o roteamento e a execução de uma tarefa de codificação.
"""

import sys
import os
sys.path.append(os.getcwd())
sys.path.append('/app')

import unittest
from unittest.mock import patch, MagicMock
from app.core.workers.router_worker import _infer_first_agent
from app.models.schemas import TaskState
from app.core.workers.thinker_agent_worker import _build_thinking_prompt

class TestThinkerFlow(unittest.TestCase):
    def test_router_infers_thinker_for_coding_tasks(self):
        print("\n[TEST] Verificando inferência do Router...")
        # Mock do planner para não falhar
        with patch("app.core.workers.router_worker.build_plan_for_goal", return_value=None):
            role = _infer_first_agent("Criar um script Python")
            self.assertEqual(role, "thinker", f"Expected 'thinker', got '{role}'")
            print("✓ Router inferiu 'thinker' corretamente.")

    def test_thinker_prompt_generation(self):
        print("\n[TEST] Verificando prompt do Thinker...")
        state = TaskState(
            original_goal="Criar uma API REST",
            data_payload={"context": "Usar FastAPI"}
        )
        prompt = _build_thinking_prompt(state)
        self.assertIn("ThinkerAgent", prompt)
        self.assertIn("API REST", prompt)
        self.assertIn("FastAPI", prompt)
        print("✓ Prompt do Thinker gerado corretamente.")

if __name__ == "__main__":
    unittest.main()
