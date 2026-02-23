import pytest

from app.db.graph import GraphDatabase


class FakeResult:
    async def single(self):
        return {"node_id": "node-1"}


class FakeTx:
    def __init__(self):
        self.query = ""
        self.params = {}

    async def run(self, query, **kwargs):
        self.query = query
        self.params = kwargs
        return FakeResult()


@pytest.mark.asyncio
async def test_merge_node_supports_composite_keys():
    tx = FakeTx()
    db = GraphDatabase()

    node_id = await db.merge_node(
        tx,
        label="Function",
        name="run",
        properties={"name": "run", "file_path": "/repo/app.py", "line": 10},
        merge_keys=["name", "file_path"],
    )

    assert node_id == "node-1"
    assert "MERGE (n:Function {name: $merge_name, file_path: $merge_file_path})" in tx.query
    assert tx.params["merge_name"] == "run"
    assert tx.params["merge_file_path"] == "/repo/app.py"
    assert tx.params["props"]["line"] == 10


@pytest.mark.asyncio
async def test_merge_node_validates_merge_keys():
    tx = FakeTx()
    db = GraphDatabase()

    with pytest.raises(ValueError, match="Invalid merge key"):
        await db.merge_node(
            tx,
            label="Function",
            name="run",
            properties={"name": "run"},
            merge_keys=["name;", "file_path"],
        )


@pytest.mark.asyncio
async def test_merge_node_requires_merge_key_values():
    tx = FakeTx()
    db = GraphDatabase()

    with pytest.raises(ValueError, match="Missing required merge key 'file_path'"):
        await db.merge_node(
            tx,
            label="Function",
            name="run",
            properties={"name": "run"},
            merge_keys=["name", "file_path"],
        )
