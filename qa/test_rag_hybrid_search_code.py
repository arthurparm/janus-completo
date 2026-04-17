import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.rag import router as rag_router
from app.core.routing import RouteDecision, RouteTarget


class _FakePolicy:
    def resolve(self, *args, **kwargs):
        return RouteDecision(
            primary=RouteTarget.QDRANT,
            secondary=(RouteTarget.NEO4J,),
            reason="test",
            rule_id="test.hybrid",
        )


class _FakeHybridService:
    async def search(self, **kwargs):
        return {
            "answer": "Resumo vetorial de Engine.run",
            "citations": [
                {
                    "source": "lexical",
                    "sources": ["lexical", "vector"],
                    "file_path": "backend/app/main.py",
                    "line": 42,
                    "score": 0.123,
                },
                {
                    "source": "graph",
                    "sources": ["graph"],
                    "concept": "Qdrant",
                    "relationship": "USES",
                    "score": 0.05,
                },
            ],
            "items": [
                {"score": 0.123},
                {"score": 0.05},
            ],
            "metrics": {"lexical_count": 1, "vector_count": 1, "graph_count": 1},
            "errors": {},
        }


def _client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(rag_router, prefix="/api/v1/rag")

    import app.api.v1.endpoints.rag as rag_module

    monkeypatch.setattr(rag_module, "get_knowledge_routing_policy", lambda: _FakePolicy())
    monkeypatch.setattr(rag_module, "get_code_hybrid_search_service", lambda: _FakeHybridService())
    return TestClient(app)


def test_hybrid_search_returns_code_results(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/v1/rag/hybrid_search?query=engine.run&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Resumo vetorial de Engine.run"
    assert payload["citations"][0]["source"] == "lexical"
    assert payload["citations"][0]["file_path"] == "backend/app/main.py"


def test_hybrid_search_keeps_existing_shape(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/v1/rag/hybrid_search?query=qdrant")

    assert response.status_code == 200
    payload = response.json()
    assert sorted(payload.keys()) == ["answer", "citations"]
