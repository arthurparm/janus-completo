import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.chat import router as chat_router
from app.config import settings
from app.core.exceptions.chat_exceptions import ChatServiceError
from app.core.infrastructure.auth import create_token, verify_token
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
        self.last_stream_user_id = None
        self.last_stream_conversation_id = None
        self.last_events_user_id = None
        self.last_events_conversation_id = None
        self.last_replaced_conversation_id = None
        self.last_replaced_text = None
        self.last_replaced_user_id = None
        self.last_message_patch = None
        self.last_history_user_id = None
        self.list_calls = 0
        self._assistant_message = {"id": "77", "role": "assistant", "text": "ok"}

    async def start_conversation_async(self, persona, user_id, project_id):
        self.last_start_user_id = user_id
        return "conv-1"

    def resolve_active_knowledge_space_id(self, conversation_id, user_id, requested_knowledge_space_id=None):
        return requested_knowledge_space_id

    async def send_message(self, **kwargs):
        self.last_message_user_id = kwargs.get("user_id")
        return {
            "response": "ok",
            "provider": "stub",
            "model": "stub-model",
            "role": "assistant",
            "conversation_id": kwargs.get("conversation_id", "conv-1"),
            "understanding": {
                "intent": "question",
                "summary": "hello",
                "confidence": 0.72,
                "requires_confirmation": False,
            },
        }

    async def list_conversations(self, **kwargs):
        self.list_calls += 1
        return []

    async def replace_last_assistant_message(self, conversation_id, new_text, user_id=None):
        self.last_replaced_conversation_id = conversation_id
        self.last_replaced_text = new_text
        self.last_replaced_user_id = user_id

    async def get_last_assistant_message(self, conversation_id, user_id=None):
        return dict(self._assistant_message)

    def get_history(self, conversation_id, user_id=None, project_id=None):
        self.last_history_user_id = user_id
        return []

    async def update_message_payload(self, conversation_id, message_id, patch, user_id=None):
        self.last_message_patch = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "patch": patch,
            "user_id": user_id,
        }
        self._assistant_message.update({"text": patch.get("text", self._assistant_message["text"])})
        return dict(self._assistant_message)

    def stream_message(self, **kwargs):
        self.last_stream_user_id = kwargs.get("user_id")
        self.last_stream_conversation_id = kwargs.get("conversation_id")

        async def _gen():
            yield 'event: protocol\ndata: {"version":"2025-11.v1"}\n\n'
            yield 'event: token\ndata: {"text":"ok"}\n\n'
            yield "event: done\ndata: [DONE]\n\n"

        return _gen()

    def stream_events(self, **kwargs):
        self.last_events_user_id = kwargs.get("user_id")
        self.last_events_conversation_id = kwargs.get("conversation_id")

        async def _gen():
            yield 'event: AgentThinking\ndata: {"agent":"dev","content":"thinking"}\n\n'

        return _gen()


class _DummyMemoryService:
    def __init__(self, items=None):
        self._items = items or []

    async def recall_filtered(self, **kwargs):
        return self._items


def _auth_headers(user_id: int | str) -> dict[str, str]:
    token = create_token(int(user_id), expires_in=3600)
    return {"Authorization": f"Bearer {token}"}


def _build_client(
    chat_service: _DummyChatService,
    memory_service: _DummyMemoryService | None = None,
    study_jobs=None,
) -> TestClient:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_memory_service] = lambda: memory_service or _DummyMemoryService()
    if study_jobs is not None:
        app.state.chat_study_job_service = study_jobs

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            actor = verify_token(token)
            if actor is not None:
                request.state.actor_user_id = str(actor)
        return await call_next(request)

    return TestClient(app)


class _DummyStudyJobs:
    def __init__(self, job):
        self._job = job

    def get_job(self, job_id):
        return self._job if job_id == self._job.job_id else None


class _OwnerScopedChatService(_DummyChatService):
    owner_user_id = "victim-user"

    def get_history(self, conversation_id, user_id=None, project_id=None):
        self.last_history_user_id = user_id
        if conversation_id == "conv-victim" and user_id and user_id != self.owner_user_id:
            raise ChatServiceError("Access denied: user_id mismatch")
        return {
            "conversation_id": conversation_id,
            "persona": None,
            "messages": [
                {
                    "timestamp": 1.0,
                    "role": "assistant",
                    "text": "private answer",
                }
            ],
        }


def test_chat_start_uses_actor_user_id_when_payload_user_absent():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.post("/api/v1/chat/start", json={}, headers=_auth_headers(42))
    assert resp.status_code == 200
    assert resp.json()["conversation_id"] == "conv-1"
    assert svc.last_start_user_id == "42"


def test_chat_message_requires_bearer_auth_without_actor_or_payload_user():
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
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "CHAT_AUTH_REQUIRED"


def test_chat_message_requires_citations_for_code_or_docs_queries():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "Onde esta a documentacao da API?",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        },
        headers=_auth_headers(1),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["citations"] == []
    assert data["citation_status"]["status"] == "missing_required"
    assert data["delivery_status"] == "pending_study"
    assert "estudando a base" in data["response"].lower()
    assert data["study_job"]["job_id"]
    assert data["message_id"] == "77"
    assert svc.last_message_patch["patch"]["delivery_status"] == "pending_study"


def test_chat_study_job_denies_access_to_other_user_with_authenticated_actor():
    svc = _DummyChatService()
    job = SimpleNamespace(
        job_id="job-victim",
        status="completed",
        progress=100,
        conversation_id="conv-victim",
        message_id="msg-1",
        placeholder_message="aguarde",
        failure_classification=None,
        final_response={"response": "private answer"},
        error=None,
        updated_at=123.0,
        user_id="victim-user",
    )
    client = _build_client(svc, study_jobs=_DummyStudyJobs(job))

    resp = client.get("/api/v1/chat/study-jobs/job-victim", headers=_auth_headers(2))

    assert resp.status_code == 403
    assert svc.last_history_user_id == "2"


def test_chat_message_low_confidence_requires_confirmation(monkeypatch):
    class _LowConfidenceService(_DummyChatService):
        async def send_message(self, **kwargs):
            return {
                "response": "executando",
                "provider": "stub",
                "model": "stub-model",
                "role": "assistant",
                "conversation_id": kwargs.get("conversation_id", "conv-1"),
                "understanding": {
                    "intent": "action_request",
                    "summary": "execute deployment",
                    "confidence": 0.72,
                    "requires_confirmation": True,
                },
            }

    monkeypatch.setenv("CHAT_CONFIDENCE_CONFIRMATION_THRESHOLD", "0.90")
    svc = _LowConfidenceService()
    client = _build_client(svc)

    resp = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "execute deploy now",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        },
        headers=_auth_headers(1),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "baixa confianca" in data["response"]
    assert data["understanding"]["requires_confirmation"] is True
    assert data["understanding"]["confirmation_reason"] == "low_confidence"
    assert data["understanding"]["confirmation"]["required"] is True
    assert data["confirmation"]["required"] is True
    assert data["agent_state"]["state"] in {"waiting_confirmation", "low_confidence"}


def test_chat_message_citations_include_clickable_source_metadata():
    svc = _DummyChatService()
    memory = _DummyMemoryService(
        [
            {
                "id": "pt-1",
                "score": 0.88,
                "content": "def run(): pass",
                "metadata": {
                    "doc_id": "doc-1",
                    "file_path": "/repo/app/main.py",
                    "line_start": 42,
                    "line_end": 44,
                    "title": "main.py",
                    "url": "https://example.invalid/main.py#L42",
                    "type": "code",
                    "origin": "workspace",
                },
            }
        ]
    )
    client = _build_client(svc, memory)

    resp = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "hello",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        },
        headers=_auth_headers(1),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["citations"]) == 1
    citation = data["citations"][0]
    assert citation["source_type"] == "code"
    assert citation["type"] == "code"
    assert citation["line_start"] == 42
    assert citation["line_end"] == 44
    assert citation["line"] == 42
    assert citation["url"] == "https://example.invalid/main.py#L42"


def test_chat_message_document_citations_prevent_pending_study(monkeypatch):
    async def _fake_collect_chat_citations(**kwargs):
        return {
            "citations": [
                {
                    "id": "doc-1",
                    "title": "genesis-backup-2026-02-05.json",
                    "file_path": "genesis-backup-2026-02-05.json",
                    "source_type": "document",
                    "type": "document",
                    "snippet": '{"version":1}',
                }
            ],
            "retrieval_failed": False,
        }

    monkeypatch.setattr(
        "app.api.v1.endpoints.chat.chat_message.collect_chat_citations",
        _fake_collect_chat_citations,
    )
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": "conv-1",
            "message": "te mandei um arquivo",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        },
        headers=_auth_headers(1),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["citation_status"]["status"] == "present"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source_type"] == "document"
    assert data.get("study_job") is None
    assert data.get("delivery_status") != "pending_study"


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


def test_chat_stream_contract_headers_events_and_actor_fallback_user():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello", "role": "orchestrator", "priority": "fast_and_cheap"},
        headers=_auth_headers(77),
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "no-cache" in resp.headers["cache-control"]
    assert resp.headers["connection"] == "keep-alive"
    assert resp.headers["x-accel-buffering"] == "no"
    assert "event: protocol" in resp.text
    assert "event: token" in resp.text
    assert "event: done" in resp.text
    assert svc.last_stream_conversation_id == "conv-1"
    assert svc.last_stream_user_id == "77"


def test_chat_stream_requires_bearer_auth_for_existing_conversation():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello", "role": "orchestrator", "priority": "fast_and_cheap"},
    )

    assert resp.status_code == 401
    assert svc.last_stream_conversation_id is None


def test_chat_stream_rejects_invalid_role_or_priority():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello", "role": "invalid", "priority": "fast_and_cheap"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "CHAT_INVALID_ROLE_OR_PRIORITY"
    assert resp.json()["detail"]["message"] == "Invalid role or priority"

    resp2 = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello", "role": "orchestrator", "priority": "invalid"},
    )
    assert resp2.status_code == 422
    assert resp2.json()["detail"]["code"] == "CHAT_INVALID_ROLE_OR_PRIORITY"
    assert resp2.json()["detail"]["message"] == "Invalid role or priority"


def test_chat_stream_reject_disallowed_origin(monkeypatch):
    svc = _DummyChatService()
    client = _build_client(svc)
    monkeypatch.setattr(settings, "CORS_ALLOW_ORIGINS", ["https://allowed.example"])

    resp = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origin not allowed"


def test_chat_events_contract_headers_event_and_actor_fallback_user():
    svc = _DummyChatService()
    client = _build_client(svc)

    resp = client.get(
        "/api/v1/chat/conv-1/events",
        headers=_auth_headers(99),
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "no-cache" in resp.headers["cache-control"]
    assert resp.headers["connection"] == "keep-alive"
    assert resp.headers["x-accel-buffering"] == "no"
    assert "event: AgentThinking" in resp.text
    assert svc.last_events_conversation_id == "conv-1"
    assert svc.last_events_user_id == "99"


def test_existing_chat_endpoints_require_bearer_auth():
    svc = _DummyChatService()
    client = _build_client(svc)

    assert client.get("/api/v1/chat/conversations").status_code == 401
    assert client.get("/api/v1/chat/conv-1/history").status_code == 401
    assert client.get("/api/v1/chat/conv-1/history/paginated").status_code == 401
    assert client.get("/api/v1/chat/conv-1/events").status_code == 401
    assert client.get("/api/v1/chat/study-jobs/job-1").status_code == 401
    assert client.put("/api/v1/chat/conv-1/rename", json={"new_title": "Renamed"}).status_code == 401
    assert client.delete("/api/v1/chat/conv-1").status_code == 401
