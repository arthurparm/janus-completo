import os
import sys

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.api.v1.endpoints.chat import router as chat_router
from app.config import settings
from app.services.chat_service import get_chat_service
from app.services.memory_service import get_memory_service


class _DummyRepo:
    def __init__(self):
        self.count_calls = 0

    def count_conversations(self) -> int:
        self.count_calls += 1
        return 7


class _DummyChatService:
    def __init__(self):
        self._repo = _DummyRepo()
        self.last_start_user_id = None
        self.last_message_user_id = None
        self.list_calls = 0

    async def start_conversation_async(self, persona, user_id, project_id):
        self.last_start_user_id = user_id
        return "conv-1"

    async def send_message(self, **kwargs):
        self.last_message_user_id = kwargs.get("user_id")
        return {
            "response": "ok",
            "provider": "stub",
            "model": "stub-model",
            "role": "assistant",
            "conversation_id": kwargs.get("conversation_id", "conv-1"),
        }

    async def list_conversations(self, **kwargs):
        self.list_calls += 1
        return []

    def stream_events(self, **kwargs):
        async def _gen():
            if False:
                yield b""

        return _gen()


class _DummyMemoryService:
    async def recall_filtered(self, **kwargs):
        return []


def _build_client(chat_service: _DummyChatService) -> TestClient:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_memory_service] = lambda: _DummyMemoryService()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_chat_start_uses_actor_user_id_when_payload_user_absent():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.post("/api/v1/chat/start", json={}, headers={"X-Actor-User-Id": "42"})
    assert resp.status_code == 200
    assert resp.json()["conversation_id"] == "conv-1"
    assert svc.last_start_user_id == "42"


def test_chat_message_uses_anonymous_fallback_without_actor_or_payload_user():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "hello",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        },
    )
    assert resp.status_code == 200
    assert isinstance(svc.last_message_user_id, str)
    assert svc.last_message_user_id.startswith("anon:")


def test_chat_health_is_non_destructive_probe():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.get("/api/v1/chat/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["repository_accessible"] is True
    assert body["non_destructive_probe"] is True
    assert body["total_conversations"] == 7
    assert svc._repo.count_calls == 1
    assert svc.list_calls == 1


def test_chat_events_reject_disallowed_origin(monkeypatch):
    svc = _DummyChatService()
    client = _build_client(svc)
    monkeypatch.setattr(settings, "CORS_ALLOW_ORIGINS", ["https://allowed.example"])

    resp = client.get(
        "/api/v1/chat/conv-1/events",
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed"
