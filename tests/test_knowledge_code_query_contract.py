import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.api.v1.endpoints.knowledge import router
from app.services.knowledge_service import get_knowledge_service


class DummyKnowledgeService:
    async def ask_code_with_citations(self, question: str, limit: int = 10, citation_limit: int = 8):
        assert question == "Onde esta Engine.run?"
        assert limit == 5
        assert citation_limit == 2
        return {
            "answer": "Engine.run esta em main.py.",
            "citations": [
                {
                    "type": "Function",
                    "name": "run",
                    "file_path": "/repo/app/main.py",
                    "line": 42,
                    "full_name": "/repo/app/main.py::Engine.run",
                    "relevance": 9,
                }
            ],
        }


class DummyKnowledgeServiceNoCitations:
    async def ask_code_with_citations(self, question: str, limit: int = 10, citation_limit: int = 8):
        return {"answer": "Resposta sem fonte", "citations": []}


def _client(service: object | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/knowledge")
    app.dependency_overrides[get_knowledge_service] = lambda: service or DummyKnowledgeService()
    return TestClient(app)


def test_query_code_with_citations_contract():
    client = _client()

    resp = client.post(
        "/api/v1/knowledge/query/code",
        json={"question": "Onde esta Engine.run?", "limit": 5, "citation_limit": 2},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Engine.run esta em main.py."
    assert len(data["citations"]) == 1
    assert data["citations"][0]["file_path"] == "/repo/app/main.py"
    assert data["citations"][0]["line"] == 42
    assert data["citations"][0]["full_name"].endswith("::Engine.run")


def test_query_code_with_citations_guard_when_missing_citations():
    client = _client(DummyKnowledgeServiceNoCitations())

    resp = client.post(
        "/api/v1/knowledge/query/code",
        json={"question": "Onde esta Engine.run?", "limit": 5, "citation_limit": 2},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["citations"] == []
    assert "Nao encontrei citacoes rastreaveis" in data["answer"]
