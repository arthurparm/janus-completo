import asyncio
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))


class _Point:
    def __init__(self, id, score, payload):
        self.id = id
        self.score = score
        self.payload = payload


class _QueryRes:
    def __init__(self, points):
        self.points = points


@pytest.fixture
def client(monkeypatch):
    import app.api.v1.endpoints.rag as mod
    from app.api.v1.endpoints.rag import router
    from app.services.memory_service import get_memory_service

    class DummyMemoryService:
        async def recall_filtered(self, query: str, filters: dict, limit: int | None, min_score=None):
            if query == "raise":
                raise RuntimeError("x")
            if query == "empty":
                return []
            return [
                {"id": "1", "content": "abc", "metadata": {"doc_id": "d1"}, "score": 0.9},
                {"id": "2", "content": "", "metadata": {}, "score": 0.1},
            ]

    class DummyQdrant:
        async def query_points(self, **kwargs):
            points = [
                _Point(
                    id="p1",
                    score=0.95,
                    payload={
                        "content": "c1",
                        "metadata": {"session_id": "s1", "role": "user", "timestamp": 1},
                    },
                ),
                _Point(
                    id="p2",
                    score=0.1,
                    payload={
                        "content": "c2",
                        "metadata": {"session_id": "s1", "role": "assistant", "timestamp": 2},
                    },
                ),
            ]
            return _QueryRes(points)

    async def _aget(*_a, **_k):
        return "coll"

    monkeypatch.setattr(mod, "aget_or_create_collection", _aget)
    monkeypatch.setattr(mod, "get_async_qdrant_client", lambda: DummyQdrant())

    async def _embed(_q: str):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(mod, "aembed_text", _embed)

    class DummyPolicy:
        def resolve(self, *args, **kwargs):
            class Decision:
                rule_id = "r1"
                primary = mod.RouteTarget.QDRANT
                secondary = [mod.RouteTarget.NEO4J]
                fallback = None

            return Decision()

    monkeypatch.setattr(mod, "get_knowledge_routing_policy", lambda: DummyPolicy())

    class DummyHybridService:
        async def search(self, **kwargs):
            if kwargs.get("query") == "raise":
                raise RuntimeError("x")
            return {
                "answer": "a",
                "citations": [
                    {"source": "lexical", "score": 0.9},
                    {"source": "vector", "score": 0.8},
                    {"source": "graph", "score": 0.7},
                ],
                "items": [{"score": 0.5}],
                "metrics": {"lexical_count": 1, "vector_count": 1, "graph_count": 1},
                "errors": {},
            }

    monkeypatch.setattr(mod, "get_code_hybrid_search_service", lambda: DummyHybridService())

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/rag")
    app.dependency_overrides[get_memory_service] = lambda: DummyMemoryService()
    yield TestClient(app)


def test_rag_search_empty_results(client):
    resp = client.get("/api/v1/rag/search?query=empty")
    assert resp.status_code == 200
    assert resp.json()["answer"]


def test_rag_search_snippets(client):
    resp = client.get("/api/v1/rag/search?query=hi")
    assert resp.status_code == 200
    assert "abc" in resp.json()["answer"]


def test_rag_search_exception_path(client):
    resp = client.get("/api/v1/rag/search?query=raise")
    assert resp.status_code == 200


def test_rag_user_chat_fallback(monkeypatch):
    import app.api.v1.endpoints.rag as mod
    from app.api.v1.endpoints.rag import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/rag")

    async def _raise(*_a, **_k):
        raise RuntimeError("x")

    monkeypatch.setattr(mod, "aget_or_create_collection", _raise)
    monkeypatch.setattr(mod, "get_knowledge_routing_policy", lambda: type("P", (), {"resolve": lambda *a, **k: type("D", (), {"rule_id": "r1", "primary": mod.RouteTarget.QDRANT, "secondary": [], "fallback": None})()})())
    client = TestClient(app)
    resp = client.get("/api/v1/rag/user-chat?query=q")
    assert resp.status_code == 200
    assert resp.json()["citations"] == []


def test_rag_user_chat_min_score_filter(client):
    resp = client.get("/api/v1/rag/user-chat?query=q&session_id=s1&min_score=0.9")
    assert resp.status_code == 200
    assert resp.json()["citations"]


def test_rag_productivity_fallback(monkeypatch):
    import app.api.v1.endpoints.rag as mod
    from app.api.v1.endpoints.rag import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/rag")

    async def _raise(*_a, **_k):
        raise RuntimeError("x")

    monkeypatch.setattr(mod, "aembed_text", _raise)
    monkeypatch.setattr(mod, "get_knowledge_routing_policy", lambda: type("P", (), {"resolve": lambda *a, **k: type("D", (), {"rule_id": "r1", "primary": mod.RouteTarget.QDRANT, "secondary": [], "fallback": None})()})())
    client = TestClient(app)
    resp = client.get("/api/v1/rag/productivity?query=q")
    assert resp.status_code == 200
    assert resp.json()["citations"] == []


def test_rag_user_chat_v2_direct_call_non_float_min_score(monkeypatch):
    import app.api.v1.endpoints.rag as mod

    class DummyQdrant:
        async def query_points(self, **kwargs):
            return []

    async def _embed(_q: str):
        return [0.1]

    monkeypatch.setattr(mod, "aembed_text", _embed)
    monkeypatch.setattr(mod, "get_async_qdrant_client", lambda: DummyQdrant())
    async def _aget(*_a, **_k):
        return "coll"

    monkeypatch.setattr(mod, "aget_or_create_collection", _aget)

    async def run():
        return await mod.rag_user_chat_search_v2(query="q", min_score="x", start_ts_ms=1, end_ts_ms=2)

    out = asyncio.run(run())
    assert out


def test_rag_hybrid_search_success(client):
    resp = client.get("/api/v1/rag/hybrid_search?query=q&limit=2")
    assert resp.status_code == 200


def test_rag_hybrid_search_exception(client):
    resp = client.get("/api/v1/rag/hybrid_search?query=raise&limit=2")
    assert resp.status_code == 200
