"""
Verification script for Semantic Commit Messages feature.
"""

import os
import sys
import unittest

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSemanticCommitService(unittest.TestCase):
    def test_suggest_commit_type_test_files(self):
        """Test that test files suggest 'test' type."""
        print(f"\n{'='*50}\nTEST: Suggest Type for Test Files\n{'='*50}")

        import asyncio

        from app.services.semantic_commit_service import suggest_commit_type

        files = ["tests/test_auth.py", "app/tests/test_service.py"]
        result = asyncio.get_event_loop().run_until_complete(suggest_commit_type(files))
        print(f"Files: {files}")
        print(f"Suggested type: {result}")
        self.assertEqual(result, "test")
        print("✅ Test files correctly suggest 'test' type.")

    def test_suggest_commit_type_docs_files(self):
        """Test that doc files suggest 'docs' type."""
        print(f"\n{'='*50}\nTEST: Suggest Type for Docs Files\n{'='*50}")

        import asyncio

        from app.services.semantic_commit_service import suggest_commit_type

        files = ["README.md", "docs/api.md"]
        result = asyncio.get_event_loop().run_until_complete(suggest_commit_type(files))
        print(f"Files: {files}")
        print(f"Suggested type: {result}")
        self.assertEqual(result, "docs")
        print("✅ Docs files correctly suggest 'docs' type.")

    def test_suggest_commit_type_ci_files(self):
        """Test that CI files suggest 'ci' type."""
        print(f"\n{'='*50}\nTEST: Suggest Type for CI Files\n{'='*50}")

        import asyncio

        from app.services.semantic_commit_service import suggest_commit_type

        files = [".github/workflows/ci.yml", "Dockerfile"]
        result = asyncio.get_event_loop().run_until_complete(suggest_commit_type(files))
        print(f"Files: {files}")
        print(f"Suggested type: {result}")
        self.assertEqual(result, "ci")
        print("✅ CI files correctly suggest 'ci' type.")

    def test_suggest_commit_type_default_feat(self):
        """Test that generic files default to 'feat'."""
        print(f"\n{'='*50}\nTEST: Default to 'feat' Type\n{'='*50}")

        import asyncio

        from app.services.semantic_commit_service import suggest_commit_type

        files = ["app/services/user_service.py", "app/api/endpoints.py"]
        result = asyncio.get_event_loop().run_until_complete(suggest_commit_type(files))
        print(f"Files: {files}")
        print(f"Suggested type: {result}")
        self.assertEqual(result, "feat")
        print("✅ Generic files correctly default to 'feat' type.")

    def test_commit_types_defined(self):
        """Test that all commit types are defined."""
        print(f"\n{'='*50}\nTEST: Commit Types Defined\n{'='*50}")

        from app.services.semantic_commit_service import COMMIT_TYPES

        expected = [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "chore",
            "ci",
            "revert",
        ]
        print(f"Expected types: {expected}")
        print(f"Defined types: {list(COMMIT_TYPES.keys())}")

        for t in expected:
            self.assertIn(t, COMMIT_TYPES)
        print("✅ All commit types are defined.")


if __name__ == "__main__":
    unittest.main()
