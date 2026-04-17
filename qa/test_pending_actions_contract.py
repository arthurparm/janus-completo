import pytest
from httpx import ASGITransport, AsyncClient

PENDING_ACTIONS_LIST_REF = "/api/v1/pending_actions/"
PENDING_ACTIONS_APPROVE_REF = "/api/v1/pending_actions/{thread_id}/approve"
PENDING_ACTIONS_REJECT_REF = "/api/v1/pending_actions/{thread_id}/reject"
PENDING_ACTIONS_APPROVE_SQL_REF = "/api/v1/pending_actions/action/{action_id}/approve"
PENDING_ACTIONS_REJECT_SQL_REF = "/api/v1/pending_actions/action/{action_id}/reject"


@pytest.fixture
def async_client():
    from app.main import app
    import app.api.v1.endpoints.pending_actions as pa
    import app.repositories.pending_action_repository as repo_mod

    original_get_state = pa._get_state
    original_update_state = pa._update_state
    original_thread_exists = pa._thread_exists_in_checkpoints
    original_resume = pa._resume_graph_execution
    original_get_graph = pa.get_graph
    original_sync_chat = pa._sync_chat_confirmation_for_action
    original_repo_class = repo_mod.PendingActionRepository

    class DummyState:
        next = "human_approval"

    async def mock_get_state(_graph, _config):
        return DummyState()

    async def mock_update_state(_graph, _config, _values):
        return None

    async def mock_thread_exists(_thread_id: str):
        return True

    async def mock_resume(_thread_id: str, _resume_value: str):
        return None

    class DummyGraph:
        pass

    pa._get_state = mock_get_state
    pa._update_state = mock_update_state
    pa._thread_exists_in_checkpoints = mock_thread_exists
    pa._resume_graph_execution = mock_resume
    pa.get_graph = lambda: DummyGraph()
    pa._sync_chat_confirmation_for_action = lambda *_args, **_kwargs: None

    class DummyAction:
        def __init__(self, id: int, status: str):
            self.id = id
            self.status = status
            self.tool_name = "tool_x"
            self.args_json = "{}"
            self.created_at = None
            self.simulation_summary_json = None
            self.simulation_generated_at = None
            self.simulation_version = None

    class DummyPendingActionRepository:
        def get(self, action_id: int):
            if action_id != 1:
                return None
            return DummyAction(id=1, status="pending")

        def set_status(self, action_id: int, status: str):
            if action_id != 1:
                return None
            return DummyAction(id=1, status=status)

        def list(self, status: str | None = "pending", limit: int = 50):
            return [DummyAction(id=1, status=status or "pending")][:limit]

    repo_mod.PendingActionRepository = DummyPendingActionRepository

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    pa._get_state = original_get_state
    pa._update_state = original_update_state
    pa._thread_exists_in_checkpoints = original_thread_exists
    pa._resume_graph_execution = original_resume
    pa.get_graph = original_get_graph
    pa._sync_chat_confirmation_for_action = original_sync_chat
    repo_mod.PendingActionRepository = original_repo_class


@pytest.mark.asyncio
class TestPendingActionsContract:
    async def test_list_pending(self, async_client):
        resp = await async_client.get(
            "/api/v1/pending_actions/?include_graph=false&include_sql=true"
        )
        assert resp.status_code == 200

    async def test_approve_thread(self, async_client):
        resp = await async_client.post("/api/v1/pending_actions/thread_1/approve")
        assert resp.status_code == 202

    async def test_reject_thread(self, async_client):
        resp = await async_client.post("/api/v1/pending_actions/thread_1/reject")
        assert resp.status_code == 202

    async def test_approve_sql_action(self, async_client):
        resp = await async_client.post("/api/v1/pending_actions/action/1/approve")
        assert resp.status_code == 202

    async def test_reject_sql_action(self, async_client):
        resp = await async_client.post("/api/v1/pending_actions/action/1/reject")
        assert resp.status_code == 202
