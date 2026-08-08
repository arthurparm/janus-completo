from __future__ import annotations

from typing import Any

from app.api.v1.endpoints.chat import router as chat_router
from app.core.security.actor_context import ActorContext, AuthMethod
from app.repositories.chat_stream_repository import ChatStreamRunState
from app.services.chat_service import get_chat_service
from app.services.chat_stream_run_service import (
    ChatStreamAttachment,
    get_chat_stream_run_service,
)
from app.services.memory_service import get_memory_service
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from qa.auth_test_support import issue_test_actor_token


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
    token = issue_test_actor_token(user_id)
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": f"chat-project-scope-{user_id}",
    }


class _PassThroughChatStreamRunService:
    async def begin_or_attach(
        self,
        *,
        owner_user_id: int,
        session_id: int | str,
        request_id: str,
        request_fingerprint: str,
        producer_factory,
    ) -> ChatStreamAttachment:
        self._chunks = [chunk async for chunk in producer_factory()]
        run = ChatStreamRunState(
            id="project-scope-run",
            owner_user_id=owner_user_id,
            session_id=1,
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            status="completed",
            last_event_sequence=len(self._chunks),
            lease_until=None,
            error_code=None,
        )
        return ChatStreamAttachment(run=run, created=True, producer_started=True)

    async def stream_events(self, *, run_id, owner_user_id, after_sequence=0):
        del run_id, owner_user_id
        for sequence, chunk in enumerate(self._chunks, start=1):
            if sequence > after_sequence:
                yield f"id: {sequence}\n{chunk}"


def _client_with_actor_project(service: _ProjectScopeChatService) -> TestClient:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_chat_stream_run_service] = (
        lambda: _PassThroughChatStreamRunService()
    )
    app.dependency_overrides[get_memory_service] = lambda: object()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        request.state.actor_context = ActorContext.authenticated(
            actor_id="1",
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="chat-project-scope-test",
        )
        return await call_next(request)

    return TestClient(app)


def test_chat_write_endpoints_use_authenticated_actor_and_explicit_project_selector():
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
    assert service.start_project_id == "client-supplied-project"
    assert service.message_project_id == "client-supplied-project"
    assert service.rename_project_id == "client-supplied-project"
    assert service.delete_project_id == "client-supplied-project"


def test_chat_read_and_stream_endpoints_use_explicit_project_selector():
    service = _ProjectScopeChatService()
    client = _client_with_actor_project(service)

    list_response = client.get(
        "/api/v1/chat/conversations?project_id=client-supplied-project",
        headers=_auth_headers(1),
    )
    stream_response = client.post(
        "/api/v1/chat/stream/conv-1",
        json={
            "message": "hello",
            "project_id": "client-supplied-project",
        },
        headers=_auth_headers(1),
    )
    events_response = client.get("/api/v1/chat/conv-1/events", headers=_auth_headers(1))

    assert list_response.status_code == 200
    assert stream_response.status_code == 200
    assert events_response.status_code == 200
    assert service.list_project_id == "client-supplied-project"
    assert service.stream_project_id == "client-supplied-project"
    assert service.events_history_project_id is None
