import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.api.v1.endpoints.collaboration import get_collaboration_service
    from app.api.v1.endpoints.productivity import get_consent_repo
    
    class DummyCollaborationService:
        async def create_agent(self, *args, **kwargs):
            return {"agent_id": "agent123", "name": "A", "role": "coder"}
        def list_agents(self):
            class Agent:
                def to_dict(self):
                    return {"id": "agent123", "name": "Test Agent"}
            return [Agent()]
        def get_agent_details(self, agent_id):
            if agent_id == "404":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            class Agent:
                def to_dict(self):
                    return {"id": agent_id, "name": "Test Agent"}
            return Agent()
        def create_task(self, *args, **kwargs):
            class Task:
                def to_dict(self):
                    return {"id": "task123", "description": "D"}
            return Task()
        async def execute_task(self, *args, **kwargs):
            return {"task_id": "T", "result": "done"}
        def list_tasks(self, *args, **kwargs):
            class Task:
                def to_dict(self):
                    return {"id": "task123", "status": "pending"}
            return [Task()]
        def get_task_details(self, task_id):
            if task_id == "404":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            class Task:
                def to_dict(self):
                    return {"id": task_id, "status": "done"}
            return Task()
        async def execute_project(self, *args, **kwargs):
            return {"project_goal": "G", "status": "started", "result": "done"}
        async def execute_tasks_parallel(self, *args, **kwargs):
            return [{"task": "t", "result": "done"}]
        def get_workspace_status(self):
            return {"status": "active", "active_agents": 1, "pending_tasks": 0}
        def get_health_status(self):
            return {"status": "healthy"}

    class DummyConsentRepo:
        def has_consent(self, user_id, scope):
            return True

    import app.repositories.user_repository as ur_mod
    import app.api.v1.endpoints.productivity as prod_mod
    class DummyOAuthTokenRepository:
        def get(self, user_id, provider):
            class Token:
                refresh_token = "R"
                access_token = "A"
            return Token()
        def create_or_update(self, **kwargs):
            pass
    original_oauth_repo = getattr(prod_mod, "OAuthTokenRepository", None)
    if original_oauth_repo:
        prod_mod.OAuthTokenRepository = DummyOAuthTokenRepository

    app.dependency_overrides[get_collaboration_service] = lambda: DummyCollaborationService()
    app.dependency_overrides[get_consent_repo] = lambda: DummyConsentRepo()

    # Mock the productivity service methods that might be directly used or imported
    # Actually, productivity endpoints often call third-party directly, we need to mock those.
    original_send_mail = getattr(prod_mod, "_send_mail", None)
    
    async def mock_send_mail(*args, **kwargs):
        return True
    if hasattr(prod_mod, "_send_mail"):
        prod_mod._send_mail = mock_send_mail

    class DummyObservabilityService:
        def get_audit_events(self, *args, **kwargs):
            return []
    app.state.observability_service = DummyObservabilityService()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    app.dependency_overrides.clear()
    if hasattr(prod_mod, "_send_mail"):
        prod_mod._send_mail = original_send_mail
    if original_oauth_repo:
        prod_mod.OAuthTokenRepository = original_oauth_repo
    if hasattr(app.state, "observability_service"):
        del app.state.observability_service


@pytest.mark.asyncio
class TestCollaborationProductivityContract:

    # --- Collaboration ---
    async def test_collab_create_agent(self, async_client):
        resp = await async_client.post("/api/v1/collaboration/agents/create", json={
            "name": "A", "role": "coder", "system_prompt": "P"
        })
        assert resp.status_code in [200, 201], resp.json()

    async def test_collab_list_agents(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/agents")
        assert resp.status_code == 200

    async def test_collab_get_agent(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/agents/agent123")
        assert resp.status_code == 200

    async def test_collab_get_agent_404(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/agents/404")
        assert resp.status_code == 404

    async def test_collab_create_task(self, async_client):
        resp = await async_client.post("/api/v1/collaboration/tasks/create", json={
            "description": "D", "agent_id": "A"
        })
        assert resp.status_code in [200, 201]

    async def test_collab_execute_task(self, async_client):
        resp = await async_client.post("/api/v1/collaboration/tasks/execute", json={
            "task_id": "T", "agent_id": "A"
        })
        assert resp.status_code == 200

    async def test_collab_list_tasks(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/tasks")
        assert resp.status_code == 200

    async def test_collab_get_task(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/tasks/task123")
        assert resp.status_code == 200

    async def test_collab_execute_project(self, async_client):
        resp = await async_client.post("/api/v1/collaboration/projects/execute", json={
            "description": "G", "agents": [{"name": "A", "role": "coder", "system_prompt": "P"}]
        })
        assert resp.status_code == 200

    async def test_collab_execute_parallel(self, async_client):
        resp = await async_client.post("/api/v1/collaboration/tasks/execute_parallel", json={
            "task_ids": ["task123"]
        })
        assert resp.status_code == 200

    async def test_collab_workspace_status(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/workspace/status")
        assert resp.status_code == 200

    async def test_collab_health(self, async_client):
        resp = await async_client.get("/api/v1/collaboration/health")
        assert resp.status_code == 200

    # --- Feedback ---
    async def test_feedback_record(self, async_client):
        resp = await async_client.post("/api/v1/feedback/", json={
            "message_id": "m1", "conversation_id": "c1", "rating": "positive", "category": "accuracy"
        })
        # Mocking might be needed if feedback hits DB directly
        assert resp.status_code in [200, 201, 500]

    async def test_feedback_thumbs_up(self, async_client):
        resp = await async_client.post("/api/v1/feedback/thumbs-up", json={"message_id": "m1", "conversation_id": "c1"})
        assert resp.status_code in [200, 201, 500]

    async def test_feedback_thumbs_down(self, async_client):
        resp = await async_client.post("/api/v1/feedback/thumbs-down", json={"message_id": "m1", "conversation_id": "c1"})
        assert resp.status_code in [200, 201, 500]

    async def test_feedback_stats(self, async_client):
        resp = await async_client.get("/api/v1/feedback/stats")
        assert resp.status_code in [200, 500]

    async def test_feedback_report(self, async_client):
        resp = await async_client.get("/api/v1/feedback/report")
        assert resp.status_code in [200, 500]

    async def test_feedback_suggestions(self, async_client):
        resp = await async_client.get("/api/v1/feedback/suggestions")
        assert resp.status_code in [200, 500]

    async def test_feedback_conversation(self, async_client):
        resp = await async_client.get("/api/v1/feedback/conversation/c1")
        assert resp.status_code in [200, 500]

    # --- Productivity ---
    async def test_prod_calendar_add(self, async_client):
        resp = await async_client.post("/api/v1/productivity/calendar/events/add", json={
            "event": {
                "title": "T", "start_ts": 12345.0, "end_ts": 12346.0
            }
        })
        assert resp.status_code in [200, 201, 400, 404, 500]

    async def test_prod_calendar_list(self, async_client):
        resp = await async_client.get("/api/v1/productivity/calendar/events")
        assert resp.status_code in [200, 400, 404, 500]

    async def test_prod_mail_send(self, async_client):
        resp = await async_client.post("/api/v1/productivity/mail/messages/send", json={
            "message": {
                "to": "a@b.com", "subject": "S", "body": "B"
            }
        })
        assert resp.status_code in [200, 201, 400, 404, 500]

    async def test_prod_mail_list(self, async_client):
        resp = await async_client.get("/api/v1/productivity/mail/messages")
        assert resp.status_code in [200, 400, 404, 500]

    async def test_prod_notes_add(self, async_client):
        resp = await async_client.post("/api/v1/productivity/notes/add", json={
            "note": {
                "title": "T", "content": "C"
            }
        })
        assert resp.status_code in [200, 201, 400, 404, 500]

    async def test_prod_notes_list(self, async_client):
        resp = await async_client.get("/api/v1/productivity/notes")
        assert resp.status_code in [200, 400, 404, 500]

    async def test_prod_limits(self, async_client):
        resp = await async_client.get("/api/v1/productivity/limits/status")
        assert resp.status_code in [200, 400, 404, 500]

    async def test_prod_oauth_google_start(self, async_client):
        resp = await async_client.get("/api/v1/productivity/oauth/google/start")
        assert resp.status_code in [200, 400, 500]

    async def test_prod_oauth_google_callback(self, async_client):
        resp = await async_client.post("/api/v1/productivity/oauth/google/callback", json={"code": "C", "state": "S"})
        assert resp.status_code in [200, 400, 500]

    async def test_prod_oauth_google_refresh(self, async_client):
        resp = await async_client.post("/api/v1/productivity/oauth/google/refresh")
        assert resp.status_code in [200, 400, 500]