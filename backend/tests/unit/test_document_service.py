import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.document_service import DocumentIngestionService


def test_process_staged_document_recovers_when_points_already_indexed(monkeypatch):
    manifest = {
        "doc_id": "doc-1",
        "user_id": "user-1",
        "storage_path": "/tmp/does-not-exist.pdf",
        "chunks_indexed": 0,
        "semantic_doc_type": "book",
        "semantic_summary": "resumo",
        "semantic_confidence": 0.91,
    }
    completed_calls = []
    failed_calls = []
    manifest_repo = SimpleNamespace(
        get_manifest=lambda doc_id: manifest,
        mark_completed=lambda *args, **kwargs: completed_calls.append((args, kwargs)),
        mark_failed=lambda *args, **kwargs: failed_calls.append((args, kwargs)),
    )
    service = DocumentIngestionService(manifest_repo=manifest_repo)

    async def fake_count_points(collection_name, query_filter):
        assert collection_name == "global_docs"
        filter_values = {
            condition.key: condition.match.value for condition in query_filter.must
        }
        assert filter_values["metadata.user_id"] == "user-1"
        assert filter_values["metadata.doc_id"] == "doc-1"
        return 7

    monkeypatch.setattr("app.services.document_service.async_count_points", fake_count_points)

    result = asyncio.run(service.process_staged_document(doc_id="doc-1"))

    assert result["status"] == "indexed"
    assert result["chunks_indexed"] == 7
    assert result["recovered_without_staged_file"] is True
    assert len(completed_calls) == 1
    assert failed_calls == []


def test_recovery_rejects_manifest_without_owner(monkeypatch):
    service = DocumentIngestionService(
        manifest_repo=SimpleNamespace(mark_completed=lambda *args, **kwargs: None)
    )

    async def unexpected_count(*args, **kwargs):
        raise AssertionError("ownerless manifest must not query a shared collection")

    monkeypatch.setattr(
        "app.services.document_service.async_count_points", unexpected_count
    )

    result = asyncio.run(
        service._recover_indexed_document_without_staged_file(
            manifest={"doc_id": "orphan", "chunks_indexed": 9}
        )
    )

    assert result is None
