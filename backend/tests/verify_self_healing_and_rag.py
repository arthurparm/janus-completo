"""
Verification script for Deep Self-Healing and Reasoning RAG.
"""
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestDeepSelfHealing(unittest.TestCase):

    def test_config_exists(self):
        """Test that self-healing config exists."""
        print(f"\n{'='*50}\nTEST: Self-Healing Config Exists\n{'='*50}")
        
        from app.config import settings
        
        self.assertTrue(hasattr(settings, 'CODER_MAX_SELF_HEALING_ITERATIONS'))
        self.assertTrue(hasattr(settings, 'CODER_SELF_HEALING_ENABLED'))
        print(f"CODER_MAX_SELF_HEALING_ITERATIONS: {settings.CODER_MAX_SELF_HEALING_ITERATIONS}")
        print(f"CODER_SELF_HEALING_ENABLED: {settings.CODER_SELF_HEALING_ENABLED}")
        self.assertEqual(settings.CODER_MAX_SELF_HEALING_ITERATIONS, 20)
        print("✅ Self-healing config exists and is correctly set.")

    def test_validate_code_syntax_valid(self):
        """Test code validation with valid Python."""
        print(f"\n{'='*50}\nTEST: Validate Valid Python Syntax\n{'='*50}")
        
        from app.core.workers.code_agent_worker import _validate_code_syntax
        
        valid_code = "def hello():\n    print('Hello')"
        result = _validate_code_syntax(valid_code)
        print(f"Code: {valid_code}")
        print(f"Result: {result}")
        self.assertTrue(result["valid"])
        print("✅ Valid code correctly validated.")

    def test_validate_code_syntax_invalid(self):
        """Test code validation with invalid Python."""
        print(f"\n{'='*50}\nTEST: Validate Invalid Python Syntax\n{'='*50}")
        
        from app.core.workers.code_agent_worker import _validate_code_syntax
        
        invalid_code = "def hello(\n    print('Hello'"
        result = _validate_code_syntax(invalid_code)
        print(f"Code: {invalid_code}")
        print(f"Result: {result}")
        self.assertFalse(result["valid"])
        self.assertIn("SyntaxError", result["error"])
        print("✅ Invalid code correctly detected.")


class TestReasoningRAG(unittest.TestCase):

    def test_config_exists(self):
        """Test that RAG config exists."""
        print(f"\n{'='*50}\nTEST: Reasoning RAG Config Exists\n{'='*50}")
        
        from app.config import settings
        
        self.assertTrue(hasattr(settings, 'RAG_HYDE_ENABLED'))
        self.assertTrue(hasattr(settings, 'RAG_RERANK_ENABLED'))
        self.assertTrue(hasattr(settings, 'RAG_RERANK_TOP_K'))
        print(f"RAG_HYDE_ENABLED: {settings.RAG_HYDE_ENABLED}")
        print(f"RAG_RERANK_ENABLED: {settings.RAG_RERANK_ENABLED}")
        print(f"RAG_RERANK_TOP_K: {settings.RAG_RERANK_TOP_K}")
        print("✅ Reasoning RAG config exists.")

    def test_service_imports(self):
        """Test that reasoning_rag_service can be imported."""
        print(f"\n{'='*50}\nTEST: Reasoning RAG Service Imports\n{'='*50}")
        
        from app.services.reasoning_rag_service import (
            generate_hypothetical_answer,
            rerank_chunks,
            enhanced_rag_search,
        )
        
        print("Imported: generate_hypothetical_answer")
        print("Imported: rerank_chunks")
        print("Imported: enhanced_rag_search")
        print("✅ All Reasoning RAG functions imported successfully.")


if __name__ == '__main__':
    unittest.main()
