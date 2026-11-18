from types import SimpleNamespace

import pytest

from app.core.memory import graph_rag_core as module


def test_graph_rag_core_module_no_longer_exposes_hybrid_retriever_shim():
    assert not hasattr(module, "HybridRetrieverShim")


def test_graph_rag_core_initializes_hybrid_retriever_directly(monkeypatch):
    captured: dict[str, object] = {}

    class FakeEmbedder:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key

    class FakeHybridRetriever:
        def __init__(self, **kwargs):
            captured["hybrid_kwargs"] = kwargs

    monkeypatch.setattr(module, "driver", object())
    monkeypatch.setattr(module, "OpenAIEmbeddings", FakeEmbedder)
    monkeypatch.setattr(module, "HybridRetriever", FakeHybridRetriever)

    core = module.GraphRAGCore()

    assert isinstance(core.retriever, FakeHybridRetriever)
    hybrid_kwargs = captured["hybrid_kwargs"]
    assert hybrid_kwargs["driver"] is core.driver
    assert hybrid_kwargs["vector_index_name"] == "janus_vector_index"
    assert hybrid_kwargs["fulltext_index_name"] == "janus_fulltext_index"
    assert hybrid_kwargs["return_properties"] == ["name", "description", "content"]


def test_graph_rag_core_degrades_when_index_is_missing(monkeypatch):
    class FakeEmbedder:
        def __init__(self, api_key: str):
            del api_key

    class FailingHybridRetriever:
        def __init__(self, **kwargs):
            del kwargs
            raise RuntimeError("No index with name janus_vector_index")

    monkeypatch.setattr(module, "driver", object())
    monkeypatch.setattr(module, "OpenAIEmbeddings", FakeEmbedder)
    monkeypatch.setattr(module, "HybridRetriever", FailingHybridRetriever)

    core = module.GraphRAGCore()

    assert core.retriever is None


@pytest.mark.asyncio
async def test_query_knowledge_graph_preserves_degraded_contract(monkeypatch):
    core = module.GraphRAGCore.__new__(module.GraphRAGCore)
    core.driver = None
    core.retriever = None

    monkeypatch.setattr(module, "_graph_rag_core", core)

    result = await module.query_knowledge_graph("where is parser", limit=3)

    assert result == "Graph RAG not initialized."


@pytest.mark.asyncio
async def test_graph_rag_core_query_without_retriever_returns_degraded_message():
    core = module.GraphRAGCore.__new__(module.GraphRAGCore)
    core.driver = None
    core.retriever = None

    result = await core.query("anything")

    assert result == "Graph RAG not initialized."
