from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import documents as documents_endpoint
from app.services.document_service import DocumentFileTooLargeError


class _FakeManifestRepo:
    def __init__(self, manifest=None, items=None):
        self.manifest = manifest
        self.items = items or []

    def list_manifests(self, **kwargs):
        return list(self.items)

    def get_manifest(self, doc_id, user_id=None):
        return self.manifest

    def delete_manifest(self, doc_id, user_id=None):
        return True


class _FakeDocumentService:
    def __init__(self, *, stage_result=None, manifest=None, items=None, stage_error=None):
        self.stage_result = stage_result or {
            "doc_id": "doc:u-1:queued",
            "status": "queued",
            "chunks": 0,
            "message": "Documento recebido e enfileirado para indexacao.",
            "status_endpoint": "/api/v1/documents/status/doc:u-1:queued",
        }
        self.stage_error = stage_error
        self.stage_calls = []
        self._manifest_repo = _FakeManifestRepo(manifest=manifest, items=items)

    async def stage_upload(self, **kwargs):
        self.stage_calls.append(kwargs)
        if self.stage_error:
            raise self.stage_error
        return dict(self.stage_result)

    def cleanup_staged_file(self, storage_path):
        return None


class _EmptyQdrantClient:
    async def scroll(self, **kwargs):
        return ([], None)

    async def delete(self, **kwargs):
        return None


def _build_client(service: _FakeDocumentService) -> TestClient:
    app = FastAPI()
    app.state.document_service = service
    app.include_router(documents_endpoint.router, prefix="/api/v1/documents")
    return TestClient(app)


def test_upload_document_returns_202_and_accepts_form_user_id(monkeypatch):
    service = _FakeDocumentService()
    monkeypatch.setattr(documents_endpoint, "get_request_actor_id", lambda request: None)
    client = _build_client(service)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("report.txt", b"conteudo", "text/plain")},
        data={"user_id_form": "u-1", "conversation_id": "conv-1"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["doc_id"] == "doc:u-1:queued"
    assert body["status"] == "queued"
    assert body["status_endpoint"].endswith("doc:u-1:queued")
    assert service.stage_calls[0]["user_id"] == "u-1"
    assert service.stage_calls[0]["conversation_id"] == "conv-1"


def test_upload_document_rejects_conflicting_user_identity(monkeypatch):
    service = _FakeDocumentService()
    monkeypatch.setattr(documents_endpoint, "get_request_actor_id", lambda request: None)
    client = _build_client(service)

    response = client.post(
        "/api/v1/documents/upload?user_id=u-query",
        files={"file": ("report.txt", b"conteudo", "text/plain")},
        data={"user_id_form": "u-form"},
    )

    assert response.status_code == 422
    assert "conflitante" in response.text


def test_upload_document_returns_413_for_streaming_oversize(monkeypatch):
    service = _FakeDocumentService(
        stage_error=DocumentFileTooLargeError(
            size_bytes=12,
            max_bytes=10,
            doc_id="doc:u-1:oversize",
        )
    )
    monkeypatch.setattr(documents_endpoint, "get_request_actor_id", lambda request: None)
    client = _build_client(service)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("big.txt", b"conteudo", "text/plain")},
        data={"user_id_form": "u-1"},
    )

    assert response.status_code == 413
    body = response.json()
    assert body["doc_id"] == "doc:u-1:oversize"
    assert body["status"] == "file_too_large"


def test_document_status_and_list_are_manifest_driven(monkeypatch):
    manifest = {
        "doc_id": "doc:u-1:1",
        "user_id": "u-1",
        "status": "processing",
        "chunks_total": 200,
        "chunks_indexed": 40,
        "error_code": None,
        "error_message": None,
        "file_name": "paper.txt",
        "conversation_id": "conv-1",
        "semantic_doc_type": "scientific_article",
        "semantic_summary": "Resumo",
        "semantic_confidence": 0.91,
        "created_at": "2026-03-10T12:00:00",
        "started_at": "2026-03-10T12:01:00",
        "completed_at": None,
    }
    service = _FakeDocumentService(manifest=manifest, items=[manifest])

    async def _fake_collection(name):
        return name

    monkeypatch.setattr(documents_endpoint, "resolve_user_scope_id", lambda request, user_id: "u-1")
    monkeypatch.setattr(documents_endpoint, "aget_or_create_collection", _fake_collection)
    monkeypatch.setattr(documents_endpoint, "get_async_qdrant_client", lambda: _EmptyQdrantClient())
    client = _build_client(service)

    status_response = client.get("/api/v1/documents/status/doc:u-1:1?user_id=u-1")
    list_response = client.get("/api/v1/documents/list?user_id=u-1&conversation_id=conv-1")

    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "processing"
    assert status_body["chunks_total"] == 200
    assert status_body["chunks_indexed"] == 40

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["doc_id"] == "doc:u-1:1"
    assert items[0]["status"] == "processing"
    assert items[0]["chunks_total"] == 200
    assert items[0]["chunks_indexed"] == 40
