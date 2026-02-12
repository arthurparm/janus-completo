from types import SimpleNamespace

import pytest

from app.repositories.knowledge_repository import KnowledgeRepository


class FakeTx:
    def __init__(self):
        self.committed = False
        self.closed = False

    async def commit(self):
        self.committed = True

    async def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, tx: FakeTx):
        self._tx = tx

    async def begin_transaction(self):
        return self._tx

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class FakeGraphDB:
    def __init__(self):
        self.tx = FakeTx()
        self.merge_node_calls = []
        self.merge_relationship_calls = []
        self.execute_calls = []

    async def get_session(self):
        return FakeSession(self.tx)

    async def merge_node(
        self,
        tx,
        label: str,
        name: str,
        properties: dict | None = None,
        merge_keys: list[str] | None = None,
    ):
        self.merge_node_calls.append(
            {
                "tx": tx,
                "label": label,
                "name": name,
                "properties": properties or {},
                "merge_keys": merge_keys or [],
            }
        )
        return f"node-{len(self.merge_node_calls)}"

    async def merge_relationship(self, tx, source_id: str, target_id: str, rel_type: str):
        self.merge_relationship_calls.append(
            {"tx": tx, "source_id": source_id, "target_id": target_id, "rel_type": rel_type}
        )

    async def execute(self, cypher_query: str, params: dict = None, operation: str | None = None):
        self.execute_calls.append(
            {"query": cypher_query, "params": params or {}, "operation": operation}
        )


@pytest.mark.asyncio
async def test_save_code_structure_uses_consistent_graph_keys():
    db = FakeGraphDB()
    repo = KnowledgeRepository(db)
    parser = SimpleNamespace(
        file_path="/repo/app/example.py",
        functions=[{"name": "run", "line": 10}],
        classes=[{"name": "Engine", "line": 30}],
    )

    await repo.save_code_structure(parser)

    assert db.tx.committed is True
    assert db.tx.closed is True
    assert len(db.merge_node_calls) == 3

    file_call = db.merge_node_calls[0]
    assert file_call["merge_keys"] == ["path"]
    assert file_call["properties"]["path"] == "/repo/app/example.py"
    assert file_call["properties"]["file_path"] == "/repo/app/example.py"

    function_call = db.merge_node_calls[1]
    assert function_call["merge_keys"] == ["name", "file_path"]
    assert function_call["properties"]["name"] == "run"
    assert function_call["properties"]["file_path"] == "/repo/app/example.py"
    assert function_call["properties"]["full_name"].endswith("::run")

    class_call = db.merge_node_calls[2]
    assert class_call["merge_keys"] == ["name", "file_path"]
    assert class_call["properties"]["name"] == "Engine"
    assert class_call["properties"]["file_path"] == "/repo/app/example.py"
    assert class_call["properties"]["full_name"].endswith("::Engine")

    assert len(db.merge_relationship_calls) == 2


@pytest.mark.asyncio
async def test_bulk_merge_calls_prefers_same_file_and_fallback():
    db = FakeGraphDB()
    repo = KnowledgeRepository(db)
    calls = [{"caller_name": "run", "callee_name": "helper", "file_path": "/repo/app/example.py"}]

    await repo.bulk_merge_calls(calls)

    assert len(db.execute_calls) == 1
    execution = db.execute_calls[0]
    query = execution["query"]
    assert "name: call.caller_name, file_path: call.file_path" in query
    assert "OPTIONAL MATCH (callee_same" in query
    assert "coalesce(callee_same, head(collect(callee_any)))" in query
    assert execution["params"]["calls"] == calls
    assert execution["operation"] == "repo_bulk_merge_calls"
