from __future__ import annotations

import asyncio
import sys
from io import BytesIO
from types import ModuleType

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

document_service_stub = ModuleType("app.services.document_service")


class _DocumentFileTooLargeError(Exception):
    def __init__(self, doc_id: str, message: str = "too large"):
        super().__init__(message)
        self.doc_id = doc_id


class _DocumentIngestionService:
    pass


document_service_stub.DocumentFileTooLargeError = _DocumentFileTooLargeError
document_service_stub.DocumentIngestionService = _DocumentIngestionService
sys.modules.setdefault("app.services.document_service", document_service_stub)

from app.api.v1.endpoints import documents


class _ManifestRepo:
    def create_manifest(self, **kwargs):
        self.created = kwargs

    def mark_completed(self, *args, **kwargs):
        self.completed = (args, kwargs)


class _DocService:
    def __init__(self):
        self._manifest_repo = _ManifestRepo()
        self.ingest_calls: list[dict[str, object]] = []
        self.stage_calls: list[dict[str, object]] = []

    async def ingest_file(self, **kwargs):
        self.ingest_calls.append(kwargs)
        return {"doc_id": "doc-1", "status": "indexed", "chunks": 1, "semantic": None}

    async def stage_upload(self, **kwargs):
        self.stage_calls.append(kwargs)
        return {"doc_id": "doc-2", "status": "queued", "chunks": 0}


def _make_upload(filename: str, content_type: str, data: bytes = b"content") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def test_upload_document_rejects_unsupported_file_type():
    service = _DocService()
    upload = _make_upload("payload.exe", "application/octet-stream")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            documents.upload_document(
                file=upload,
                request=None,
                service=service,
                conversation_id=None,
                knowledge_space_id=None,
                source_type=None,
                source_id=None,
                doc_role=None,
                edition_or_version=None,
                language=None,
                parent_collection_id=None,
            )
        )

    assert exc_info.value.status_code == 400
    assert "não suportado" in str(exc_info.value.detail).lower()
    assert service.stage_calls == []


def test_link_url_rejects_private_hosts():
    service = _DocService()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            documents.link_url(
                url="http://localhost/internal",
                conversation_id=None,
                knowledge_space_id=None,
                source_type=None,
                source_id=None,
                doc_role=None,
                edition_or_version=None,
                language=None,
                parent_collection_id=None,
                request=None,
                service=service,
            )
        )

    assert exc_info.value.status_code == 400
    assert service.ingest_calls == []


def test_link_url_accepts_public_http_url(monkeypatch):
    service = _DocService()

    def fake_getaddrinfo(host: str, port: int):
        return [(None, None, None, None, ("93.184.216.34", port))]

    class _Response:
        headers = {"content-type": "text/html"}
        content = b"<html><body>ok</body></html>"

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, follow_redirects: bool = False):
            assert follow_redirects is False
            return _Response()

    monkeypatch.setattr(documents.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=10: _Client())

    result = asyncio.run(
        documents.link_url(
            url="https://docs.example.org/guide.html",
            conversation_id=None,
            knowledge_space_id=None,
            source_type=None,
            source_id=None,
            doc_role=None,
            edition_or_version=None,
            language=None,
            parent_collection_id=None,
            request=None,
            service=service,
        )
    )

    assert result.status == "indexed"
    assert service.ingest_calls[0]["filename"] == "guide.html"
