import unittest
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.data_retention_service import DataRetentionService
from app.db.sync_events import register_cleanup_events
from app.models.user_models import User

class TestGhostDataMitigation(unittest.TestCase):

    @patch("app.services.data_retention_service.delete_points_by_filter")
    @patch("app.db.graph.GraphDatabase")
    def test_cleanup_trigger(self, mock_graph, mock_vector_delete):
        """
        Verify that calling cleanup_user_artifacts triggers the correct repository methods.
        Note: Integration with real DBs would require running infrastructure.
        Here we verify the logic flow and service orchestration.
        """
        print(f"\n{'='*50}\nTEST: DataRetentionService Orchestration\n{'='*50}")
        
        user_id = 9999
        
        # Capture async call to knowledge repo
        mock_repo_instance = MagicMock()
        mock_repo_instance.delete_user_data = MagicMock(return_value= asyncio.Future())
        mock_repo_instance.delete_user_data.return_value.set_result(0)

        with patch("app.services.data_retention_service.get_knowledge_repository", return_value=mock_repo_instance):
            with patch("app.services.data_retention_service.get_graph_db", return_value=asyncio.Future()) as mock_get_db:
                mock_get_db.return_value.set_result(MagicMock())
                
                # EXECUTE
                asyncio.run(DataRetentionService.cleanup_user_artifacts(user_id))
        
        # VERIFY QDRANT
        print("[CHECK] Vector Store Deletion...")
        mock_vector_delete.assert_any_call("janus_memory", {})
        mock_vector_delete.assert_any_call("janus_knowledge", {})
        print("✅ Qdrant delete called for both collections.")

        # VERIFY NEO4J
        print("[CHECK] Graph Store Deletion...")
        mock_repo_instance.delete_user_data.assert_called_once_with()
        print("✅ Neo4j delete called.")

    def test_sqlalchemy_listener_registration(self):
        """
        Verify that the listener function is correctly imported and can be registered without error.
        """
        print(f"\n{'='*50}\nTEST: Event Listener Registration\n{'='*50}")
        try:
            register_cleanup_events()
            print("✅ Listener registered successfully on User model.")
        except Exception as e:
            self.fail(f"Registration failed: {e}")

if __name__ == '__main__':
    unittest.main()
