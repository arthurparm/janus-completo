import pytest

from app.core.infrastructure.resilience import CircuitOpenError
from app.services.knowledge_graph_service import KnowledgeGraphService


class _FakeGraphDb:
    def __init__(self, fail_on_call: int):
        self.calls = 0
        self.fail_on_call = fail_on_call

    async def query(self, _cypher, _params=None):
        self.calls += 1
        if self.calls >= self.fail_on_call:
            raise CircuitOpenError("Circuit Breaker esta ABERTO para 'neo4j_query'")
        return [{"ok": True}]


@pytest.mark.asyncio
async def test_persist_extraction_aborts_relationship_batch_when_circuit_opens(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb(fail_on_call=1)

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)

    extracted_data = {
        "entities": [],
        "relationships": [
            {"source": "A", "target": "B", "relation": "RELATED_TO"},
            {"source": "B", "target": "C", "relation": "RELATED_TO"},
        ],
    }

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-1",
        extracted_data=extracted_data,
        source_metadata={},
    )

    assert entities_created == 0
    assert relationships_created == 0
    assert fake_db.calls == 1


@pytest.mark.asyncio
async def test_persist_extraction_aborts_entity_batch_when_circuit_opens(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb(fail_on_call=1)

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)

    extracted_data = {
        "entities": [
            {"name": "Entity A", "type": "concept"},
            {"name": "Entity B", "type": "concept"},
        ],
        "relationships": [],
    }

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-2",
        extracted_data=extracted_data,
        source_metadata={},
    )

    assert entities_created == 0
    assert relationships_created == 0
    assert fake_db.calls == 1
