import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.services.chat_service import get_chat_service
    from app.services.memory_service import get_memory_service
    
    class DummyChatService:
        async def list_conversations(self, **kwargs):
            return [{"conversation_id": "conv-1", "title": "Conv 1"}]
            
        def get_history(self, conversation_id, user_id=None, project_id=None):
            return {
                "conversation_id": conversation_id,
                "persona": "default",
                "messages": [
                    {"role": "user", "text": "hi", "timestamp": 123}
                ]
            }

        def get_history_paginated(self, conversation_id, limit=50, offset=0, before_ts=None, after_ts=None, user_id=None, project_id=None):
            return {
                "conversation_id": conversation_id,
                "persona": "default",
                "messages": [
                    {"role": "user", "text": "hi", "timestamp": 123}
                ],
                "total_count": 1,
                "has_more": False,
                "next_offset": None,
                "limit": limit
            }
            
        async def rename_conversation(self, conversation_id, title, user_id=None, project_id=None):
            if conversation_id == "conv-404":
                from app.services.chat_service import ConversationNotFoundError
                raise ConversationNotFoundError("Not found")
            if conversation_id == "conv-403":
                from app.services.chat_service import ChatServiceError
                raise ChatServiceError("Forbidden")
            if conversation_id == "conv-1":
                return True
            return False
            
        async def delete_conversation(self, conversation_id, user_id=None, project_id=None):
            if conversation_id == "conv-404":
                from app.services.chat_service import ConversationNotFoundError
                raise ConversationNotFoundError("Not found")
            if conversation_id == "conv-403":
                from app.services.chat_service import ChatServiceError
                raise ChatServiceError("Forbidden")
            if conversation_id == "conv-1":
                return True
            return False
            
    class DummyMemoryService:
        async def fetch_paginated_history(self, **kwargs):
            return {
                "items": [{"role": "user", "content": "hi"}],
                "next_cursor": None,
                "has_more": False
            }
            
        async def get_trace(self, conversation_id):
            return {"steps": ["thought 1", "thought 2"]}
            
    from app.services.trace_service import get_trace_service
    class DummyTraceService:
        def get_trace(self, conversation_id):
            return {"steps": ["thought 1", "thought 2"]}
            
    app.dependency_overrides[get_trace_service] = lambda: DummyTraceService()
    
    from app.services.observability_service import get_observability_service
    class DummyObservabilityService:
        def register_event(self, *args, **kwargs):
            pass
            
    import logging
    class RaiseLog(logging.Handler):
        def emit(self, record):
            if record.exc_info:
                import traceback
                traceback.print_exception(*record.exc_info)
    logging.getLogger("app.api.exception_handlers").addHandler(RaiseLog())
            
    app.dependency_overrides[get_chat_service] = lambda: DummyChatService()
    
    import app.api.exception_handlers as exc_handlers
    exc_handlers.global_exception_handler = None
    exc_handlers.http_exception_handler = None
    
    app.dependency_overrides[get_memory_service] = lambda: DummyMemoryService()
    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()
    
    import app.api.v1.endpoints.chat.deps as chat_deps
    original_resolve = chat_deps.resolve_authenticated_user_context
    from app.api.v1.endpoints.chat.deps import ChatIdentityResolution
    chat_deps.resolve_authenticated_user_context = lambda *args, **kwargs: ChatIdentityResolution(
        user_id="1",
        identity_source="mock",
        auth_present=True,
        authenticated=True
    )
    
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client
    
    chat_deps.resolve_authenticated_user_context = original_resolve
    app.dependency_overrides.clear()

@pytest.mark.asyncio
class TestChatHistoryContract:

    async def test_list_conversations(self, async_client):
        resp = await async_client.get("/api/v1/chat/conversations")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["conversation_id"] == "conv-1"

    async def test_get_history(self, async_client):
        resp = await async_client.get("/api/v1/chat/conv-1/history")
        assert resp.status_code == 200, resp.json()
        assert "messages" in resp.json()
        assert len(resp.json()["messages"]) == 1

    async def test_get_history_paginated(self, async_client):
        resp = await async_client.get("/api/v1/chat/conv-1/history/paginated?limit=10")
        assert resp.status_code == 200, resp.json()
        assert "messages" in resp.json()
        assert len(resp.json()["messages"]) == 1

    async def test_rename_conversation(self, async_client):
        resp = await async_client.put(
            "/api/v1/chat/conv-1/rename",
            json={"new_title": "New Title"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_rename_conversation_not_found(self, async_client):
        resp = await async_client.put(
            "/api/v1/chat/conv-404/rename",
            json={"new_title": "New Title"}
        )
        assert resp.status_code == 404

    async def test_rename_conversation_forbidden(self, async_client):
        resp = await async_client.put(
            "/api/v1/chat/conv-403/rename",
            json={"new_title": "New Title"}
        )
        assert resp.status_code == 403

    async def test_delete_conversation(self, async_client):
        resp = await async_client.delete("/api/v1/chat/conv-1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_delete_conversation_not_found(self, async_client):
        resp = await async_client.delete("/api/v1/chat/conv-404")
        assert resp.status_code == 404

    async def test_chat_health(self, async_client):
        # We need to mock _repo.count_conversations inside the DummyChatService
        import app.api.v1.endpoints.chat.chat_admin as admin_mod
        from app.main import app
        chat_service = app.dependency_overrides.get(admin_mod.get_chat_service)()
        class DummyRepo:
            def count_conversations(self):
                return 1
        chat_service._repo = DummyRepo()
        
        # apply it to the override
        app.dependency_overrides[admin_mod.get_chat_service] = lambda: chat_service
        
        resp = await async_client.get("/api/v1/chat/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    async def test_get_conversation_trace(self, async_client):
        resp = await async_client.get("/api/v1/chat/conv-1/trace")
        assert resp.status_code == 200
        assert "steps" in resp.json()
