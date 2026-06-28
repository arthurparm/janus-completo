import pytest
from app.core.infrastructure.auth import create_token, verify_token
from httpx import ASGITransport, AsyncClient

PENDING_ACTIONS_LIST_REF = "/api/v1/pending_actions/"
PENDING_ACTIONS_APPROVE_REF = "/api/v1/pending_actions/{thread_id}/approve"
PENDING_ACTIONS_REJECT_REF = "/api/v1/pending_actions/{thread_id}/reject"
PENDING_ACTIONS_APPROVE_SQL_REF = "/api/v1/pending_actions/action/{action_id}/approve"
PENDING_ACTIONS_REJECT_SQL_REF = "/api/v1/pending_actions/action/{action_id}/reject"


def _auth_headers(user_id: str) -> dict[str, str]:
    token = create_token(int(user_id), expires_in=3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def async_client():
    import app.api.v1.endpoints.pending_actions as pa
    import app.repositories.pending_action_repository as repo_mod
    from app.api.v1.endpoints.chat.deps import ChatIdentityResolution
    from app.main import app
    from app.services.chat_service import get_chat_service

    original_get_state = pa._get_state
    original_update_state = pa._update_state
    original_thread_exists = pa._thread_exists_in_checkpoints
    original_resume = pa._resume_graph_execution
    original_get_graph = pa.get_graph
    original_get_session_context_manager = pa._get_session_context_manager
    original_sync_chat = pa._sync_chat_confirmation_for_action
    original_resolve_identity = pa.resolve_authenticated_user_context
    original_repo_class = repo_mod.PendingActionRepository
    original_chat_override = app.dependency_overrides.get(get_chat_service)

    class DummyState:
        def __init__(self, *, next_value: str = "human_approval", values=None, metadata=None, config=None):
            self.next = next_value
            self.values = values or {}
            self.metadata = metadata or {}
            self.config = config or {}

    async def mock_get_state(_graph, config):
        thread_id = config["configurable"]["thread_id"]
        if thread_id == "thread-owner-1":
            return DummyState(metadata={"owner_user_id": "1"})
        if thread_id == "thread-owner-2":
            return DummyState(metadata={"owner_user_id": "2"})
        if thread_id == "thread-conv-owner-1":
            return DummyState(values={"conversation_id": "conv-owner-1"})
        if thread_id == "thread-no-owner":
            return DummyState()
        if thread_id == "thread-finished":
            return DummyState(next_value="")
        return DummyState(metadata={"owner_user_id": "1"})

    async def mock_update_state(_graph, _config, _values):
        return None

    async def mock_thread_exists(thread_id: str):
        if thread_id == "thread-missing":
            return False
        return True

    async def mock_resume(_thread_id: str, _resume_value: str):
        return None

    class DummyGraph:
        pass

    class DummyResult:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class DummySession:
        async def execute(self, _query, _params=None):
            return DummyResult(
                [
                    ("thread-owner-1",),
                    ("thread-owner-2",),
                    ("thread-conv-owner-1",),
                    ("thread-no-owner",),
                ]
            )

    class DummySessionContext:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    pa._get_state = mock_get_state
    pa._update_state = mock_update_state
    pa._thread_exists_in_checkpoints = mock_thread_exists
    pa._resume_graph_execution = mock_resume
    pa.get_graph = lambda: DummyGraph()
    pa._get_session_context_manager = lambda _postgres_db: DummySessionContext()
    pa._sync_chat_confirmation_for_action = lambda *_args, **_kwargs: None

    def _resolve_from_bearer(http, explicit_user_id, **kwargs):
        del explicit_user_id
        del kwargs
        auth = http.headers.get("Authorization") or ""
        actor = None
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            verified = verify_token(token)
            actor = str(verified) if verified is not None else None
        return ChatIdentityResolution(
            user_id=actor,
            identity_source="actor" if actor else "unknown",
            auth_present=bool(auth),
            authenticated=bool(actor),
        )

    pa.resolve_authenticated_user_context = _resolve_from_bearer

    class DummyChatService:
        def get_history(self, conversation_id, user_id=None, project_id=None):
            if conversation_id == "conv-owner-1" and user_id == "1":
                return {"conversation_id": conversation_id, "messages": []}
            if conversation_id == "conv-foreign" and user_id != "1":
                raise pa.ChatServiceError("Access denied: user_id mismatch")
            if conversation_id == "conv-owner-1":
                raise pa.ChatServiceError("Access denied: user_id mismatch")
            return {"conversation_id": conversation_id, "messages": []}

    class DummyAction:
        def __init__(
            self,
            id: int,
            status: str,
            *,
            user_id: str | None = "1",
            args_json: str = "{}",
        ):
            self.id = id
            self.status = status
            self.user_id = user_id
            self.tool_name = "tool_x"
            self.args_json = args_json
            self.created_at = None
            self.simulation_summary_json = None
            self.simulation_generated_at = None
            self.simulation_version = None

    class DummyPendingActionRepository:
        def get(self, action_id: int, user_id: str | None = None):
            if action_id != 1:
                if action_id == 2:
                    action = DummyAction(id=2, status="pending", user_id="2")
                    if user_id is not None and user_id != action.user_id:
                        return None
                    return action
                if action_id == 3:
                    action = DummyAction(
                        id=3,
                        status="pending",
                        user_id=None,
                        args_json='{"conversation_id":"conv-owner-1"}',
                    )
                    if user_id is not None and user_id != action.user_id:
                        return None
                    return action
                return None
            action = DummyAction(id=1, status="pending", user_id="1")
            if user_id is not None and user_id != action.user_id:
                return None
            return action

        def set_status(self, action_id: int, status: str, user_id: str | None = None):
            action = self.get(action_id, user_id=user_id)
            if action is None:
                return None
            return DummyAction(
                id=action.id,
                status=status,
                user_id=action.user_id,
                args_json=action.args_json,
            )

        def list(self, status: str | None = "pending", limit: int = 50, user_id: str | None = None):
            items = [
                DummyAction(id=1, status=status or "pending", user_id="1"),
                DummyAction(id=2, status=status or "pending", user_id="2"),
            ]
            if user_id is not None:
                items = [item for item in items if item.user_id == user_id]
            return items[:limit]

    repo_mod.PendingActionRepository = DummyPendingActionRepository
    app.dependency_overrides[get_chat_service] = lambda: DummyChatService()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    pa._get_state = original_get_state
    pa._update_state = original_update_state
    pa._thread_exists_in_checkpoints = original_thread_exists
    pa._resume_graph_execution = original_resume
    pa.get_graph = original_get_graph
    pa._get_session_context_manager = original_get_session_context_manager
    pa._sync_chat_confirmation_for_action = original_sync_chat
    pa.resolve_authenticated_user_context = original_resolve_identity
    repo_mod.PendingActionRepository = original_repo_class
    if original_chat_override is None:
        app.dependency_overrides.pop(get_chat_service, None)
    else:
        app.dependency_overrides[get_chat_service] = original_chat_override


@pytest.mark.asyncio
class TestPendingActionsContract:
    async def test_list_pending(self, async_client):
        resp = await async_client.get(
            "/api/v1/pending_actions/?include_graph=false&include_sql=true",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) == 1
        assert payload[0]["user_id"] == "1"

    async def test_list_pending_graph_requires_bearer(self, async_client):
        resp = await async_client.get("/api/v1/pending_actions/?include_graph=true&include_sql=false")
        assert resp.status_code == 401

    async def test_list_pending_graph_returns_only_accessible_threads(self, async_client):
        resp = await async_client.get(
            "/api/v1/pending_actions/?include_graph=true&include_sql=false",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 200
        payload = resp.json()
        thread_ids = {item["thread_id"] for item in payload}
        assert "thread-owner-1" in thread_ids
        assert "thread-conv-owner-1" in thread_ids
        assert "thread-owner-2" not in thread_ids
        assert "thread-no-owner" not in thread_ids

    async def test_approve_thread_requires_bearer(self, async_client):
        resp = await async_client.post("/api/v1/pending_actions/thread-owner-1/approve")
        assert resp.status_code == 401

    async def test_approve_thread_owned(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-owner-1/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 202

    async def test_approve_thread_denies_other_user(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-owner-2/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 403

    async def test_approve_thread_denies_missing_owner_context(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-no-owner/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 403

    async def test_approve_thread_missing_returns_404(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-missing/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 404

    async def test_reject_thread_allows_conversation_fallback(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-conv-owner-1/reject",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 202

    async def test_reject_thread_missing_returns_404(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/thread-missing/reject",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 404

    async def test_approve_sql_action(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/action/1/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 202

    async def test_reject_sql_action(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/action/1/reject",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 202

    async def test_reject_sql_action_denies_other_user(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/action/2/reject",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 403

    async def test_approve_sql_action_legacy_without_owner_is_blocked(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/action/3/approve",
            headers=_auth_headers("1"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "PENDING_ACTION_OWNER_REQUIRED"

    async def test_approve_sql_action_legacy_without_owner_blocks_any_user(self, async_client):
        resp = await async_client.post(
            "/api/v1/pending_actions/action/3/approve",
            headers=_auth_headers("2"),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "PENDING_ACTION_OWNER_REQUIRED"
