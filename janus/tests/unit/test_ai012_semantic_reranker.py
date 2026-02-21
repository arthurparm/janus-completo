import pytest

from app.config import settings
from app.services.semantic_reranker_service import SemanticRerankerService


@pytest.mark.asyncio
async def test_rerank_disabled_returns_passthrough(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", False)
    svc = SemanticRerankerService()
    items = [{"content": "a", "score": 0.9}, {"content": "b", "score": 0.8}]

    result = await svc.rerank(query="a", items=items, top_k=1)

    assert result.applied is False
    assert result.method == "disabled"
    assert result.items == [items[0]]


@pytest.mark.asyncio
async def test_rerank_heuristic_prioritizes_overlap(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "RAG_RERANK_BACKEND", "heuristic")
    svc = SemanticRerankerService()
    items = [
        {"content": "calendario e eventos mensais", "score": 0.95},
        {"content": "validar cpf em python com testes", "score": 0.30},
    ]

    result = await svc.rerank(query="python validar cpf", items=items, top_k=1)

    assert result.applied is True
    assert result.method == "heuristic"
    assert result.items[0]["content"].startswith("validar cpf")


@pytest.mark.asyncio
async def test_rerank_cross_encoder_falls_back_to_heuristic(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "RAG_RERANK_BACKEND", "cross_encoder")
    svc = SemanticRerankerService()
    items = [{"content": "foo bar", "score": 0.2}, {"content": "bar baz", "score": 0.1}]

    async def _none():
        return None

    monkeypatch.setattr(svc, "_get_cross_encoder", _none)
    result = await svc.rerank(query="foo", items=items, top_k=2)

    assert result.applied is True
    assert result.method == "heuristic"


@pytest.mark.asyncio
async def test_rerank_cross_encoder_combines_scores(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "RAG_RERANK_BACKEND", "cross_encoder")
    monkeypatch.setattr(settings, "RAG_RERANK_CROSS_ENCODER_WEIGHT", 1.0)
    monkeypatch.setattr(settings, "RAG_RERANK_BASE_SCORE_WEIGHT", 0.0)

    svc = SemanticRerankerService()
    items = [
        {"content": "item-A", "score": 0.9},
        {"content": "item-B", "score": 0.1},
    ]

    class _FakeCrossEncoder:
        def predict(self, _pairs):
            return [0.1, 0.9]

    async def _fake_get():
        return _FakeCrossEncoder()

    monkeypatch.setattr(svc, "_get_cross_encoder", _fake_get)
    result = await svc.rerank(query="q", items=items, top_k=1)

    assert result.method == "cross_encoder"
    assert result.items[0]["content"] == "item-B"


@pytest.mark.asyncio
async def test_rerank_heuristic_can_boost_metadata_alignment(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "RAG_RERANK_BACKEND", "heuristic")
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_TEXT_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_BASE_WEIGHT", 0.2)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_METADATA_WEIGHT", 0.8)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_RECENCY_WEIGHT", 0.0)

    svc = SemanticRerankerService()
    items = [
        {
            "content": "Politica de dados pessoais e consentimento.",
            "score": 0.1,
            "metadata": {"type": "doc_chunk", "semantic_doc_type": "policy_legal"},
        },
        {
            "content": "Politica de dados pessoais e consentimento.",
            "score": 0.9,
            "metadata": {"type": "doc_chunk", "semantic_doc_type": "technical_doc"},
        },
    ]

    result = await svc.rerank(query="politica lgpd dados pessoais", items=items, top_k=1)

    assert result.applied is True
    assert result.method == "heuristic"
    assert result.items[0]["metadata"]["semantic_doc_type"] == "policy_legal"


@pytest.mark.asyncio
async def test_rerank_heuristic_can_boost_recency(monkeypatch):
    monkeypatch.setattr(settings, "RAG_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "RAG_RERANK_BACKEND", "heuristic")
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_TEXT_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_BASE_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_METADATA_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "RAG_RERANK_HEURISTIC_RECENCY_WEIGHT", 1.0)

    svc = SemanticRerankerService()
    items = [
        {
            "content": "contexto relevante",
            "score": 0.5,
            "metadata": {"type": "doc_chunk", "timestamp": 1000},
        },
        {
            "content": "contexto relevante",
            "score": 0.5,
            "metadata": {"type": "doc_chunk", "timestamp": 9000},
        },
    ]

    result = await svc.rerank(query="contexto relevante", items=items, top_k=1)

    assert result.applied is True
    assert result.method == "heuristic"
    assert result.items[0]["metadata"]["timestamp"] == 9000
