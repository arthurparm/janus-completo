"""
Verification script for Stateful Workers (Context Caching) feature.
"""
import unittest
import sys
import os

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestContextCache(unittest.TestCase):

    def test_store_and_retrieve(self):
        """Test that context can be stored and retrieved."""
        print(f"\n{'='*50}\nTEST: Store and Retrieve\n{'='*50}")
        
        from app.core.infrastructure.context_cache import ContextCache
        
        cache = ContextCache(ttl_seconds=60)
        task_id = "test-task-123"
        static_context = {
            "original_goal": "Build a REST API",
            "meta": {"user_id": 1, "project_id": 2}
        }
        
        # Store
        context_hash = cache.store(task_id, static_context)
        print(f"Stored context with hash: {context_hash[:8]}...")
        self.assertIsNotNone(context_hash)
        
        # Retrieve
        retrieved = cache.retrieve(task_id)
        print(f"Retrieved context: {retrieved}")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["original_goal"], "Build a REST API")
        print("✅ Store and retrieve works correctly.")

    def test_cache_miss(self):
        """Test that missing entries return None."""
        print(f"\n{'='*50}\nTEST: Cache Miss\n{'='*50}")
        
        from app.core.infrastructure.context_cache import ContextCache
        
        cache = ContextCache()
        result = cache.retrieve("non-existent-task")
        print(f"Result for non-existent: {result}")
        self.assertIsNone(result)
        print("✅ Cache miss correctly returns None.")

    def test_invalidate(self):
        """Test that invalidation removes entries."""
        print(f"\n{'='*50}\nTEST: Invalidate\n{'='*50}")
        
        from app.core.infrastructure.context_cache import ContextCache
        
        cache = ContextCache()
        task_id = "task-to-invalidate"
        cache.store(task_id, {"goal": "test"})
        
        # Verify stored
        self.assertIsNotNone(cache.retrieve(task_id))
        
        # Invalidate
        cache.invalidate(task_id)
        
        # Verify gone
        self.assertIsNone(cache.retrieve(task_id))
        print("✅ Invalidation works correctly.")

    def test_task_state_fields_exist(self):
        """Test that TaskState has new caching fields."""
        print(f"\n{'='*50}\nTEST: TaskState Fields\n{'='*50}")
        
        from app.models.schemas import TaskState
        
        state = TaskState(original_goal="Test goal")
        print(f"context_cached: {state.context_cached}")
        print(f"static_context_hash: {state.static_context_hash}")
        
        self.assertFalse(state.context_cached)
        self.assertIsNone(state.static_context_hash)
        
        # Simulate caching
        state.context_cached = True
        state.static_context_hash = "abc123"
        
        self.assertTrue(state.context_cached)
        self.assertEqual(state.static_context_hash, "abc123")
        print("✅ TaskState caching fields work correctly.")


if __name__ == '__main__':
    unittest.main()
