import pytest

from app.services import knowledge_service as knowledge_module
from app.services.knowledge_service import KnowledgeService


class _FakeRepo:
    async def find_code_citations(self, tokens, limit=8):
        return [
            {
                "type": "Function",
                "name": "run",
                "file_path": "/repo/app/main.py",
                "line": 10,
                "full_name": "/repo/app/main.py::run",
                "relevance": 9,
            }
        ]


@pytest.mark.asyncio
async def test_semantic_query_emits_required_telemetry(monkeypatch):
    emitted: list[dict] = []

    async def _fake_query(question: str, limit: int = 10) -> str:
        assert question == "where is parser"
        assert limit == 3
        return "parser is in app/services/code_analysis_service.py"

    def _fake_emit(**kwargs):
        emitted.append(kwargs)
        return kwargs

    monkeypatch.setattr(knowledge_module, "query_knowledge_graph", _fake_query)
    monkeypatch.setattr(knowledge_module, "emit_step_telemetry", _fake_emit)

    service = KnowledgeService(_FakeRepo())
    answer = await service.semantic_query("where is parser", limit=3)

    assert "code_analysis_service.py" in answer
    assert emitted
    event = emitted[-1]
    assert event["step"] == "semantic_query"
    assert event["source"] == "graph_rag"
    assert event["db"] == "neo4j"
    assert isinstance(event["latency_ms"], float)
    assert "confidence" in event
    assert "error_code" in event


@pytest.mark.asyncio
async def test_ask_code_with_citations_emits_code_citations_telemetry(monkeypatch):
    emitted: list[dict] = []

    async def _fake_query(question: str, limit: int = 10) -> str:
        return f"answer:{question}:{limit}"

    def _fake_emit(**kwargs):
        emitted.append(kwargs)
        return kwargs

    monkeypatch.setattr(knowledge_module, "query_knowledge_graph", _fake_query)
    monkeypatch.setattr(knowledge_module, "emit_step_telemetry", _fake_emit)

    service = KnowledgeService(_FakeRepo())
    result = await service.ask_code_with_citations(
        question="How does run call helper", limit=4, citation_limit=2
    )

    assert result["answer"] == "answer:How does run call helper?:4"
    assert len(result["citations"]) == 1
    code_events = [event for event in emitted if event.get("step") == "code_citations"]
    assert code_events
    event = code_events[-1]
    assert event["source"] == "knowledge_service"
    assert event["db"] == "neo4j"
    assert event["extra"]["citation_count"] == 1
