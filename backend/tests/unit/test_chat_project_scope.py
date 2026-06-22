from __future__ import annotations

from typing import Any

from app.api.v1.endpoints.chat import router as chat_router
from app.core.infrastructure.auth import create_token
from app.services.chat_service import get_chat_service
from app.services.memory_service import get_memory_service
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class _ProjectScopeChatService:
    def __init__(self) -> None:
        self.start_project_id: str | None = None
        self.message_project_id: str | None = None
        self.stream_project_id: str | None = None
        self.list_project_id: str | None = None
        self.rename_project_id: str | None = None
        self.delete_project_id: str | None = None
        self.events_history_project_id: str | None = None

    async def start_conversation_async(
        self, persona: str | None, user_id: str | None, project_id: str | None
    ) -> str:
        self.start_project_id = project_id
        return "conv-1"

    def resolve_active_knowledge_space_id(
        self,
        *,
        conversation_id: str,
        user_id: str | None = None,
        requested_knowledge_space_id: str | None = None,
    ) -> str | None:
        return requested_knowledge_space_id

    async def send_message(self, **kwargs: Any) -> dict[str, Any]:
        self.message_project_id = kwargs.get("project_id")
        return {
            "response": "ok",
            "provider": "stub",
            "model": "stub-model",
            "role": "assistant",
            "conversation_id": kwargs.get("conversation_id", "conv-1"),
            "citations": [],
            "citation_status": {"mode": "optional", "status": "not_applicable", "count": 0},
            "understanding": {
                "intent": "question",
                "summary": "project scope",
                "confidence": 0.9,
                "requires_confirmation": False,
            },
        }

    def get_history(
        self,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        self.events_history_project_id = project_id
        return {"conversation_id": conversation_id, "persona": None, "messages": []}

    async def list_conversations(
        self,
        user_id: str | None = None,
        project_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self.list_project_id = project_id
        return []

    async def rename_conversation(
        self,
        conversation_id: str,
        new_title: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        self.rename_project_id = project_id

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        self.delete_project_id = project_id

    def stream_message(self, **kwargs: Any):
        self.stream_project_id = kwargs.get("project_id")

        async def _gen():
            yield 'event: done\ndata: {"done": true}\n\n'

        return _gen()

    def stream_events(self, conversation_id: str, user_id: str | None = None):
        async def _gen():
            yield 'event: done\ndata: {"done": true}\n\n'

        return _gen()


def _auth_headers(user_id: int | str) -> dict[str, str]:
    token = create_token(int(user_id), expires_in=3600)
    return {"Authorization": f"Bearer {token}"}


def _client_with_actor_project(service: _ProjectScopeChatService) -> TestClient:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_memory_service] = lambda: object()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        request.state.actor_user_id = "user-1"
        request.state.actor_project_id = "project-from-auth"
        return await call_next(request)

    return TestClient(app)


def test_chat_write_endpoints_prefer_authenticated_project_scope():
    service = _ProjectScopeChatService()
    client = _client_with_actor_project(service)

    start_response = client.post(
        "/api/v1/chat/start",
        json={"persona": "assistant", "project_id": "client-supplied-project"},
        headers=_auth_headers(1),
    )
    message_response = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "hello",
            "project_id": "client-supplied-project",
        },
        headers=_auth_headers(1),
    )
    rename_response = client.put(
        "/api/v1/chat/conv-1/rename",
        json={"new_title": "Renamed", "project_id": "client-supplied-project"},
        headers=_auth_headers(1),
    )
    delete_response = client.delete(
        "/api/v1/chat/conv-1?project_id=client-supplied-project",
        headers=_auth_headers(1),
    )

    assert start_response.status_code == 200
    assert message_response.status_code == 200
    assert rename_response.status_code == 200
    assert delete_response.status_code == 200
    assert service.start_project_id == "project-from-auth"
    assert service.message_project_id == "project-from-auth"
    assert service.rename_project_id == "project-from-auth"
    assert service.delete_project_id == "project-from-auth"


def test_chat_read_and_stream_endpoints_prefer_authenticated_project_scope():
    service = _ProjectScopeChatService()
    client = _client_with_actor_project(service)

    list_response = client.get(
        "/api/v1/chat/conversations?project_id=client-supplied-project",
        headers=_auth_headers(1),
    )
    stream_response = client.get(
        "/api/v1/chat/stream/conv-1",
        params={
            "message": "hello",
            "project_id": "client-supplied-project",
        },
        headers=_auth_headers(1),
    )
    events_response = client.get("/api/v1/chat/conv-1/events", headers=_auth_headers(1))

    assert list_response.status_code == 200
    assert stream_response.status_code == 200
    assert events_response.status_code == 200
    assert service.list_project_id == "project-from-auth"
    assert service.stream_project_id == "project-from-auth"
    assert service.events_history_project_id == "project-from-auth"
