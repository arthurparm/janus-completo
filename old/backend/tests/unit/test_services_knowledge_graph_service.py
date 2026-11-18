import pytest
from unittest.mock import AsyncMock

from app.core.infrastructure.resilience import CircuitOpenError
from app.services.knowledge_graph_service import KnowledgeGraphService


class _FakeGraphDb:
    def __init__(self, fail_on_call: int | None = None):
        self.calls = 0
        self.fail_on_call = fail_on_call
        self.history: list[tuple[str, dict | None]] = []

    async def query(self, _cypher, _params=None):
        self.calls += 1
        self.history.append((_cypher, _params))
        if self.fail_on_call is not None and self.calls >= self.fail_on_call:
            raise CircuitOpenError("Circuit Breaker esta ABERTO para 'neo4j_query'")
        if "alias_added_count" in str(_cypher):
            return [{"ok": True, "alias_added_count": 1}]
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


@pytest.mark.asyncio
async def test_persist_extraction_normalizes_and_dedupes_batch(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb()

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)

    extracted_data = {
        "entities": [
            {"name": "Teste", "type": "concept", "description": "primeiro"},
            {"name": "TESTE", "type": "concept", "description": "duplicado"},
            {"name": "Preferência do usuário: responder em tópicos curtos", "type": "concept"},
            {"name": "Preferência do Usuário: responder em tópicos curtos", "type": "concept"},
        ],
        "relationships": [
            {"source": "Teste", "target": "TESTE", "relation": "related_to", "weight": 0.6},
            {"source": "TESTE", "target": " teste ", "relation": "RELATED_TO", "weight": 0.9},
            {
                "source": "Preferência do usuário: responder em tópicos curtos",
                "target": "Preferência do Usuário: responder em tópicos curtos",
                "relation": "related_to",
            },
        ],
    }

    # Auto-loops normalizados são descartados para quarentena; patch para não acessar DB real de quarentena.
    monkeypatch.setattr(service, "_send_to_quarantine", AsyncMock())

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-normalize",
        extracted_data=extracted_data,
        source_metadata={},
    )

    # 4 entidades brutas colapsam em 2 writes (por canonical_name)
    assert entities_created == 2
    # 3 relações viram auto-loop após normalização e são quarentenadas
    assert relationships_created == 0

    entity_calls = [c for c in fake_db.history if "MERGE (e:Entity {canonical_name" in c[0]]
    rel_calls = [c for c in fake_db.history if "MERGE (source)-[r:" in c[0]]
    assert len(entity_calls) == 2
    assert len(rel_calls) == 0

    first_entity_params = entity_calls[0][1] or {}
    assert "canonical_name" in first_entity_params
    assert "aliases" in first_entity_params
    assert any(alias in {"Teste", "TESTE"} for alias in first_entity_params["aliases"])


@pytest.mark.asyncio
async def test_persist_extraction_translates_relates_to_to_related_to(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb()

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)

    extracted_data = {
        "entities": [
            {"name": "Alpha", "type": "concept"},
            {"name": "Beta", "type": "concept"},
        ],
        "relationships": [
            {"source": "Alpha", "target": "Beta", "relation": "related_to"},
        ],
    }

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-rel-map",
        extracted_data=extracted_data,
        source_metadata={},
    )

    assert entities_created == 2
    assert relationships_created == 1

    rel_calls = [c for c in fake_db.history if "MERGE (source)-[r:" in c[0]]
    assert len(rel_calls) == 1
    assert ":RELATED_TO" in rel_calls[0][0]
    assert ":RELATES_TO" not in rel_calls[0][0]
    rel_params = rel_calls[0][1] or {}
    assert rel_params["source_canonical"] == "alpha"
    assert rel_params["target_canonical"] == "beta"


@pytest.mark.asyncio
async def test_persist_extraction_dedupes_duplicate_relationships_in_same_batch(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb()

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)

    extracted_data = {
        "entities": [
            {"name": "Alpha", "type": "concept"},
            {"name": "Beta", "type": "concept"},
        ],
        "relationships": [
            {"source": "Alpha", "target": "Beta", "relation": "related_to", "weight": 0.4},
            {"source": "ALPHA", "target": "beta", "relation": "RELATED_TO", "weight": 0.9},
            {"source": " alpha ", "target": "Beta", "relation": "related_to", "weight": 0.7},
        ],
    }

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-rel-dedupe",
        extracted_data=extracted_data,
        source_metadata={},
    )

    assert entities_created == 2
    assert relationships_created == 1

    rel_calls = [c for c in fake_db.history if "MERGE (source)-[r:" in c[0]]
    assert len(rel_calls) == 1
    params = rel_calls[0][1] or {}
    assert params["source_canonical"] == "alpha"
    assert params["target_canonical"] == "beta"
    # Mantém peso consolidado (max) para evitar inflar no lote.
    assert params["weight"] == 0.9


@pytest.mark.asyncio
async def test_persist_extraction_quarantines_normalized_self_loop(monkeypatch):
    service = KnowledgeGraphService()
    fake_db = _FakeGraphDb()

    async def _get_db():
        return fake_db

    monkeypatch.setattr(service, "get_db", _get_db)
    quarantine_mock = AsyncMock()
    monkeypatch.setattr(service, "_send_to_quarantine", quarantine_mock)

    extracted_data = {
        "entities": [{"name": "Teste", "type": "concept"}],
        "relationships": [
            {"source": "Teste", "target": "TESTE", "relation": "related_to"},
        ],
    }

    entities_created, relationships_created = await service.persist_extraction(
        experience_id="exp-self-loop",
        extracted_data=extracted_data,
        source_metadata={},
    )

    assert entities_created == 1
    assert relationships_created == 0
    quarantine_mock.assert_awaited_once()
    rel_calls = [c for c in fake_db.history if "MERGE (source)-[r:" in c[0]]
    assert rel_calls == []
