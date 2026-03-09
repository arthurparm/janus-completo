import pytest

from app.services.chat import chat_citation_service as citation_module


class _FakeHit:
    def __init__(self, *, point_id: str, score: float, payload: dict):
        self.id = point_id
        self.score = score
        self.payload = payload


class _FakeClient:
    def __init__(self):
        self.scroll_calls = 0

    async def query_points(self, **kwargs):
        return type("Resp", (), {"points": []})()

    async def scroll(self, **kwargs):
        self.scroll_calls += 1
        return (
            [
                _FakeHit(
                    point_id="doc-1",
                    score=0.0,
                    payload={
                        "content": '{"version":1,"createdAt":"2026-02-05"}',
                        "metadata": {
                            "type": "doc_chunk",
                            "user_id": "u-1",
                            "conversation_id": "conv-1",
                            "doc_id": "doc:u-1:1",
                            "file_name": "genesis-backup-2026-02-05.json",
                        },
                    },
                )
            ],
            None,
        )


class _FakeMemory:
    async def recall_filtered(self, **kwargs):
        return []


@pytest.mark.asyncio
async def test_collect_chat_citations_falls_back_to_conversation_documents_for_file_reference(
    monkeypatch,
):
    client = _FakeClient()

    async def _fake_embed(text: str):
        return [0.1, 0.2, 0.3]

    async def _fake_collection(name: str):
        return name

    monkeypatch.setattr(citation_module, "aembed_text", _fake_embed)
    monkeypatch.setattr(citation_module, "aget_or_create_collection", _fake_collection)
    monkeypatch.setattr(citation_module, "get_async_qdrant_client", lambda: client)

    result = await citation_module.collect_chat_citations(
        message="te mandei um arquivo",
        user_id="u-1",
        conversation_id="conv-1",
        memory_service=_FakeMemory(),
        limit=3,
    )

    assert client.scroll_calls == 1
    assert result["retrieval_failed"] is False
    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["source_type"] == "document"
    assert citation["title"] == "genesis-backup-2026-02-05.json"
    assert "createdAt" in str(citation["snippet"])
