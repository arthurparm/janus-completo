import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.knowledge import router


class _DummyKnowledgeFacade:
    def health_snapshot(self):
        return {
            "active_backend": "baseline_qdrant",
            "shadow_backend": "experimental_quantized_retrieval",
            "experimental_collection_suffix": "-turboquant",
            "experimental_index_enabled": True,
            "experimental_index_version": "v1",
            "experimental_write_dual": False,
            "compare_on_read": True,
            "promotion_allowed": False,
            "last_build": {"domain": "docs"},
        }

    async def build_experimental_index(self, **kwargs):
        return SimpleNamespace(
            dry_run=True,
            output_dir="/tmp/knowledge-experimental",
            manifest=SimpleNamespace(**{"domain": kwargs["domain"], "version": "v1"}),
        )

    async def compare_retrieval(self, **kwargs):
        return {
            "active": [{"id": "doc-1", "doc_id": "doc-1", "score": 0.9}],
            "shadow": [{"id": "doc-1", "doc_id": "doc-1", "score": 0.8}],
            "compare_diff": {"overlap_ratio": 1.0, "only_active": [], "only_shadow": []},
        }


def _client() -> TestClient:
    app = FastAPI()
    app.state.knowledge_facade = _DummyKnowledgeFacade()
    app.include_router(router, prefix="/api/v1/knowledge")
    return TestClient(app)


def test_experimental_health_snapshot_contract():
    client = _client()

    response = client.get("/api/v1/knowledge/experimental/health")

    assert response.status_code == 200
    data = response.json()
    assert data["active_backend"] == "baseline_qdrant"
    assert data["shadow_backend"] == "experimental_quantized_retrieval"
    assert data["experimental_index_enabled"] is True


def test_experimental_build_contract():
    client = _client()

    response = client.post(
        "/api/v1/knowledge/experimental/index/build",
        json={"domain": "docs", "dry_run": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["manifest"]["domain"] == "docs"


def test_experimental_compare_contract():
    client = _client()

    response = client.post(
        "/api/v1/knowledge/experimental/compare",
        json={"operation": "search_documents", "query": "janus", "limit": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compare_diff"]["overlap_ratio"] == 1.0
    assert data["active"][0]["doc_id"] == "doc-1"
