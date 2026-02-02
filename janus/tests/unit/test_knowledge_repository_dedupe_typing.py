import pytest

from app.models.schemas import GraphRelationship
from app.repositories.knowledge_repository import KnowledgeRepository


class FakeResult:
    async def single(self):
        return None


class FakeTx:
    def __init__(self, sink):
        self.sink = sink

    async def run(self, query, **kwargs):
        self.sink.append(query)
        return FakeResult()

    async def commit(self):
        pass


class FakeSession:
    def __init__(self, sink):
        self.sink = sink

    async def begin_transaction(self):
        return FakeTx(self.sink)

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class FakeGraphDB:
    def __init__(self, responses):
        self.responses = responses
        self.sink = []

    async def query(self, cypher_query: str, params: dict = None, operation: str | None = None):
        return self.responses.get(operation or "", [])

    async def execute(self, cypher_query: str, params: dict = None, operation: str | None = None):
        # Record executes for inspection when needed
        self.sink.append(cypher_query)

    async def get_session(self):
        return FakeSession(self.sink)

    async def register_relationship_type(self, tx_or_session, rel_type: str):
        pass


@pytest.mark.asyncio
async def test_dedupe_functions_and_classes_uses_enum_types(monkeypatch):
    calls = []

    def _audit(event):
        calls.append(event.get("action"))

    monkeypatch.setattr("app.repositories.knowledge_repository.record_audit_event_direct", _audit)

    responses = {
        "repo_dedupe_functions_scan": [{"name": "fn", "fp": "/path", "fs": [1, 2]}],
        "repo_dedupe_classes_scan": [{"name": "Cls", "fp": "/path", "cs": [3, 4]}],
    }
    db = FakeGraphDB(responses)
    repo = KnowledgeRepository(db)
    result = await repo.dedupe_functions_and_classes()
    assert result["functions_fixed"] == 1
    assert result["classes_fixed"] == 1
    q = "\n".join(db.sink)
    assert f"`{GraphRelationship.CALLS.value}`" in q
    assert f"`{GraphRelationship.IMPLEMENTS.value}`" in q
    assert "dedupe_functions_and_classes" in calls


@pytest.mark.asyncio
async def test_dedupe_concepts_uses_relates_to(monkeypatch):
    calls = []

    def _audit(event):
        calls.append(event.get("action"))

    monkeypatch.setattr("app.repositories.knowledge_repository.record_audit_event_direct", _audit)

    responses = {
        "repo_dedupe_concepts_scan": [{"name": "ConceptX", "cs": [1, 2]}],
    }
    db = FakeGraphDB(responses)
    repo = KnowledgeRepository(db)
    result = await repo.dedupe_concepts()
    assert result["fixed"] == 1
    q = "\n".join(db.sink)
    assert f"`{GraphRelationship.RELATES_TO.value}`" in q
    assert "dedupe_concepts" in calls


@pytest.mark.asyncio
async def test_dedupe_files_uses_relates_to(monkeypatch):
    calls = []

    def _audit(event):
        calls.append(event.get("action"))

    monkeypatch.setattr("app.repositories.knowledge_repository.record_audit_event_direct", _audit)

    responses = {
        "repo_dedupe_files_scan": [{"p": "/path", "fs": [1, 2]}],
    }
    db = FakeGraphDB(responses)
    repo = KnowledgeRepository(db)
    result = await repo.dedupe_files()
    assert result["files_fixed"] == 1
    q = "\n".join(db.sink)
    assert f"`{GraphRelationship.RELATES_TO.value}`" in q
    assert "dedupe_files" in calls


@pytest.mark.asyncio
async def test_bulk_merge_calls_metrics_and_audit(monkeypatch):
    calls = []

    def _audit(event):
        calls.append(event.get("action"))

    monkeypatch.setattr("app.repositories.knowledge_repository.record_audit_event_direct", _audit)

    db = FakeGraphDB({})
    repo = KnowledgeRepository(db)
    await repo.bulk_merge_calls(
        [
            {"caller_name": "a", "callee_name": "b", "file_path": "/p"},
            {"caller_name": "c", "callee_name": "d", "file_path": "/p"},
        ]
    )
    q = "\n".join(db.sink)
    assert GraphRelationship.CALLS.value in q
    assert "bulk_merge_calls" in calls
