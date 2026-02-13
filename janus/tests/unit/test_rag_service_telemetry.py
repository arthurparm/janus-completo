import pytest

from app.services import rag_service as rag_module
from app.services.rag_service import RAGService


class _DummyRepo:
    def get_conversation(self, conversation_id: str):
        return {"messages": []}


class _DummyMemory:
    async def index_interaction(self, content: str, user_id: str, session_id: str, role: str) -> None:
        return None


class _FakeHit:
    def __init__(self, score: float, content: str):
        self.score = score
        self.payload = {
            "content": content,
            "metadata": {"type": "doc_chunk", "user_id": "u-1"},
        }


class _FakeQueryResponse:
    def __init__(self, points):
        self.points = points


class _FakeClient:
    async def query_points(self, **kwargs):
        return _FakeQueryResponse(points=[_FakeHit(0.83, "Important context")])


@pytest.mark.asyncio
async def test_retrieve_context_emits_telemetry_with_required_fields(monkeypatch):
    emitted: list[dict] = []

    async def _fake_embed(text: str):
        return [0.1, 0.2, 0.3]

    async def _fake_collection(name: str):
        return "user_u-1"

    def _fake_emit(**kwargs):
        emitted.append(kwargs)
        return kwargs

    monkeypatch.setattr(rag_module, "aembed_text", _fake_embed)
    monkeypatch.setattr(rag_module, "aget_or_create_collection", _fake_collection)
    monkeypatch.setattr(rag_module, "get_async_qdrant_client", lambda: _FakeClient())
    monkeypatch.setattr(rag_module, "emit_step_telemetry", _fake_emit)

    service = RAGService(repo=_DummyRepo(), llm_service=object(), memory_service=_DummyMemory())
    context = await service.retrieve_context("find context", user_id="u-1", conversation_id="c-1")

    assert context is not None
    assert "Important context" in context
    assert emitted
    event = emitted[-1]
    assert event["step"] == "retrieve_context"
    assert event["source"] == "rag_service"
    assert event["db"] == "qdrant"
    assert "latency_ms" in event
    assert "confidence" in event
    assert "error_code" in event


@pytest.mark.asyncio
async def test_retrieve_context_emits_skip_telemetry_when_user_missing(monkeypatch):
    emitted: list[dict] = []

    def _fake_emit(**kwargs):
        emitted.append(kwargs)
        return kwargs

    monkeypatch.setattr(rag_module, "emit_step_telemetry", _fake_emit)

    service = RAGService(repo=_DummyRepo(), llm_service=object(), memory_service=_DummyMemory())
    context = await service.retrieve_context("find context", user_id=None, conversation_id="c-1")

    assert context is None
    assert emitted
    event = emitted[-1]
    assert event["step"] == "retrieve_context"
    assert event["error_code"] == "SKIPPED_MISSING_USER_ID"
