import os
import sys

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.knowledge import router
from app.services.knowledge_service import get_knowledge_service
from app.services.knowledge_space_service import get_knowledge_space_service


class _DummyKnowledgeService:
    async def get_stats(self):
        return {}


class _DummyKnowledgeSpaceService:
    def __init__(self):
        self.created = None
        self.attached = None
        self.consolidated = None
        self.queried = None

    def create_space(self, **kwargs):
        self.created = kwargs
        return {
            "knowledge_space_id": "ks:1",
            "name": kwargs["name"],
            "source_type": kwargs["source_type"],
            "source_id": kwargs.get("source_id"),
            "edition_or_version": kwargs.get("edition_or_version"),
            "language": kwargs.get("language"),
            "parent_collection_id": kwargs.get("parent_collection_id"),
            "description": kwargs.get("description"),
            "consolidation_status": "not_started",
            "consolidation_summary": None,
            "last_consolidated_at": None,
            "sections_total": 0,
            "sections_indexed": 0,
            "sections_skipped_as_noise": 0,
            "canonical_frames_total": 0,
            "consolidation_quality_score": 0.0,
        }

    def list_spaces(self, **kwargs):
        return [
            {
                "knowledge_space_id": "ks:1",
                "name": "Livro Base",
                "source_type": "book",
                "source_id": "book-1",
                "edition_or_version": "1e",
                "language": "pt-BR",
                "parent_collection_id": None,
                "description": None,
                "consolidation_status": "ready",
                "consolidation_summary": "ok",
                "last_consolidated_at": None,
                "sections_total": 8,
                "sections_indexed": 6,
                "sections_skipped_as_noise": 2,
                "canonical_frames_total": 5,
                "consolidation_quality_score": 0.82,
            }
        ]

    async def attach_document(self, **kwargs):
        self.attached = kwargs
        return {"doc_id": kwargs["doc_id"], "knowledge_space_id": kwargs["knowledge_space_id"]}

    async def consolidate_space(self, **kwargs):
        self.consolidated = kwargs
        return {
            "knowledge_space_id": kwargs["knowledge_space_id"],
            "status": "ready",
            "documents_total": 2,
            "sections_total": 8,
            "canonical_points_indexed": 8,
        }

    def get_space(self, *, knowledge_space_id: str):
        return {
            "knowledge_space_id": knowledge_space_id,
            "name": "Livro Base",
            "source_type": "book",
            "source_id": "book-1",
            "edition_or_version": "1e",
            "language": "pt-BR",
            "parent_collection_id": None,
            "description": None,
            "consolidation_status": "processing",
            "consolidation_summary": "queued",
            "last_consolidated_at": None,
            "sections_total": 0,
            "sections_indexed": 0,
            "sections_skipped_as_noise": 0,
            "canonical_frames_total": 0,
            "consolidation_quality_score": 0.0,
        }

    def get_space_status(self, *, knowledge_space_id: str):
        return {
            "knowledge_space_id": knowledge_space_id,
            "name": "Livro Base",
            "source_type": "book",
            "source_id": "book-1",
            "edition_or_version": "1e",
            "language": "pt-BR",
            "parent_collection_id": None,
            "description": None,
            "consolidation_status": "processing",
            "consolidation_summary": "queued",
            "last_consolidated_at": None,
            "documents_total": 2,
            "documents_indexed": 1,
            "documents_processing": 1,
            "documents_queued": 0,
            "documents_failed": 0,
            "chunks_total": 10,
            "chunks_indexed": 4,
            "progress": 0.4,
            "sections_total": 8,
            "sections_indexed": 6,
            "sections_skipped_as_noise": 2,
            "canonical_frames_total": 5,
            "consolidation_quality_score": 0.82,
        }

    def mark_consolidation_requested(self, *, knowledge_space_id: str):
        self.consolidated = {
            "knowledge_space_id": knowledge_space_id,
            "status": "processing",
        }
        return {
            "knowledge_space_id": knowledge_space_id,
            "consolidation_status": "processing",
        }

    async def query_space(self, **kwargs):
        self.queried = kwargs
        return {
            "answer": "Base consolidada indica:\n- Capítulo 1: introdução.",
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "answer_strategy": "sequence",
            "evidence_count": 1,
            "source_roles_used": ["base"],
            "source_scope": {"knowledge_space_id": kwargs["knowledge_space_id"]},
            "citations": [{"doc_id": "doc-1", "file_name": "livro.pdf"}],
            "confidence": 0.91,
            "gaps_or_conflicts": [],
        }


def _build_client(service: _DummyKnowledgeSpaceService) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/knowledge")
    app.dependency_overrides[get_knowledge_service] = lambda: _DummyKnowledgeService()
    app.dependency_overrides[get_knowledge_space_service] = lambda: service
    import app.api.v1.endpoints.knowledge as knowledge_module

    async def _fake_publish_consolidation_task(payload, correlation_id=None):
        return {"status": "ok", "task_id": "task-123", "payload": payload, "correlation_id": correlation_id}

    knowledge_module.publish_consolidation_task = _fake_publish_consolidation_task

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_create_knowledge_space_uses_actor_scope():
    service = _DummyKnowledgeSpaceService()
    client = _build_client(service)

    resp = client.post(
        "/api/v1/knowledge/spaces",
        json={"name": "Livro Base", "source_type": "book"},
        headers={"X-Actor-User-Id": "77"},
    )

    assert resp.status_code == 200
    assert resp.json()["knowledge_space_id"] == "ks:1"
    assert service.created["source_type"] == "book"


def test_attach_and_consolidate_knowledge_space():
    service = _DummyKnowledgeSpaceService()
    client = _build_client(service)

    attach = client.post(
        "/api/v1/knowledge/spaces/ks:1/documents/doc-9/attach",
        json={"source_id": "vol-1"},
    )
    assert attach.status_code == 200
    assert service.attached["knowledge_space_id"] == "ks:1"
    assert service.attached["doc_id"] == "doc-9"

    consolidate = client.post(
        "/api/v1/knowledge/spaces/ks:1/consolidate",
        json={"limit_docs": 12},
    )
    assert consolidate.status_code == 200
    data = consolidate.json()
    assert data["message"] == "Consolidação estrutural publicada."
    assert data["stats"]["status"] == "ok"
    assert data["stats"]["task_id"]
    assert "status_url" in data["stats"]

    status = client.get("/api/v1/knowledge/spaces/ks:1")
    assert status.status_code == 200
    assert status.json()["documents_processing"] == 1
    assert status.json()["progress"] == 0.4


def test_query_knowledge_space_returns_canonical_shape():
    service = _DummyKnowledgeSpaceService()
    client = _build_client(service)

    resp = client.post(
        "/api/v1/knowledge/spaces/ks:1/query",
        json={"question": "qual a sequência", "mode": "canonical_answer"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode_used"] == "canonical_answer"
    assert data["base_used"] == "consolidated"
    assert data["citations"][0]["doc_id"] == "doc-1"
    assert service.queried["question"] == "qual a sequência"
