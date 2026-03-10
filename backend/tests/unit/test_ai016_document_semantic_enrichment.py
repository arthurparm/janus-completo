import pytest

from app.config import settings
from app.services import document_service as document_module
from app.services.document_semantic_enrichment_service import DocumentSemanticEnrichmentService
from app.services.document_service import DocumentIngestionService


class _CountResult:
    def __init__(self, count: int):
        self.count = count


class _FakeQdrantClient:
    def __init__(self):
        self.upsert_points = None
        self.deleted = False

    async def count(self, **_kwargs):
        return _CountResult(0)

    async def delete(self, **_kwargs):
        self.deleted = True
        return None

    async def upsert(self, *, collection_name, points):
        self.upsert_points = points
        return {"collection": collection_name, "count": len(points)}


def test_semantic_enrichment_disabled_returns_unknown(monkeypatch):
    monkeypatch.setattr(settings, "AI_DOC_ENRICHMENT_ENABLED", False)
    svc = DocumentSemanticEnrichmentService()

    result = svc.enrich(
        text="Documento com python e fastapi.",
        filename="notes.txt",
        content_type="text/plain",
    )

    assert result.doc_type == "unknown"
    assert result.entities == {}
    assert result.summary == ""
    assert result.confidence == 0.0


def test_semantic_enrichment_detects_code_and_entities(monkeypatch):
    monkeypatch.setattr(settings, "AI_DOC_ENRICHMENT_ENABLED", True)
    svc = DocumentSemanticEnrichmentService()

    text = (
        "Implementar endpoint FastAPI em Python. "
        "Contato: dev@janus.ai. "
        "Ticket ABC-123. "
        "Mais detalhes em https://docs.janus.ai."
    )
    result = svc.enrich(
        text=text,
        filename="service.py",
        content_type="text/plain",
    )

    assert result.doc_type == "code"
    assert result.entities.get("emails") == ["dev@janus.ai"]
    assert result.entities.get("ticket_ids") == ["ABC-123"]
    assert result.entities.get("urls") == ["https://docs.janus.ai"]
    assert "python" in result.entities.get("technologies", [])
    assert result.summary


@pytest.mark.asyncio
async def test_ingest_file_includes_semantic_metadata_in_payload(monkeypatch):
    monkeypatch.setattr(settings, "AI_DOC_ENRICHMENT_ENABLED", True)

    fake_client = _FakeQdrantClient()

    async def _fake_embed_texts(chunks):
        return [[0.1, 0.2, 0.3] for _ in chunks]

    async def _fake_get_collection(_name):
        return "user_u-1"

    monkeypatch.setattr(document_module, "aembed_texts", _fake_embed_texts)
    monkeypatch.setattr(document_module, "aget_or_create_collection", _fake_get_collection)
    monkeypatch.setattr(document_module, "get_async_qdrant_client", lambda: fake_client)

    service = DocumentIngestionService(memory_service=object())
    service._parser.parse = lambda *_args, **_kwargs: (
        "Privacy policy objetivo: explicar uso de dados e conformidade LGPD. "
        "Contato legal@janus.ai. URL https://janus.ai/privacy."
    )

    result = await service.ingest_file(
        user_id="u-1",
        filename="privacy.txt",
        content_type="text/plain",
        data=b"fake",
        conversation_id="c-1",
    )

    assert result["status"] == "indexed"
    assert result["semantic"]["doc_type"] == "policy_legal"
    assert fake_client.upsert_points is not None
    assert len(fake_client.upsert_points) >= 1

    first_payload = fake_client.upsert_points[0].payload
    metadata = first_payload["metadata"]
    assert metadata["semantic_doc_type"] == "policy_legal"
    assert metadata["semantic_summary"]
    assert metadata["semantic_entities"]["emails"] == ["legal@janus.ai"]
