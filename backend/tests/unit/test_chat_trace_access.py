from app.api.v1.endpoints.chat import router as chat_router
from app.services.chat_service import ChatServiceError, get_chat_service
from app.services.trace_service import get_trace_service
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class _DenyingChatService:
    def __init__(self) -> None:
        self.history_calls = 0

    def get_history(self, conversation_id, user_id=None, project_id=None):
        self.history_calls += 1
        raise ChatServiceError("Access denied: user_id mismatch")


class _TraceService:
    def __init__(self) -> None:
        self.trace_calls = 0

    def get_trace(self, conversation_id):
        self.trace_calls += 1
        return {"steps": ["should-not-leak"]}


def test_trace_endpoint_checks_chat_access_before_returning_trace():
    chat_service = _DenyingChatService()
    trace_service = _TraceService()
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_trace_service] = lambda: trace_service

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        request.state.actor_user_id = "user-1"
        return await call_next(request)

    client = TestClient(app)
    response = client.get("/api/v1/chat/conv-2/trace")

    assert response.status_code == 403
    assert chat_service.history_calls == 1
    assert trace_service.trace_calls == 0
