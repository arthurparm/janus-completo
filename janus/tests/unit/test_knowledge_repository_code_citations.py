import pytest

from app.repositories.knowledge_repository import KnowledgeRepository


class FakeGraphDB:
    def __init__(self, query_rows=None):
        self.query_rows = query_rows or []
        self.query_calls = []

    async def query(self, cypher_query: str, params: dict = None, operation: str | None = None):
        self.query_calls.append(
            {"query": cypher_query, "params": params or {}, "operation": operation}
        )
        return self.query_rows


@pytest.mark.asyncio
async def test_find_code_citations_skips_query_when_tokens_empty():
    db = FakeGraphDB()
    repo = KnowledgeRepository(db)

    rows = await repo.find_code_citations(tokens=[], limit=5)

    assert rows == []
    assert db.query_calls == []


@pytest.mark.asyncio
async def test_find_code_citations_queries_with_file_and_line():
    db = FakeGraphDB(
        query_rows=[
            {
                "type": "Function",
                "name": "run",
                "file_path": "/repo/app/main.py",
                "line": 42,
                "full_name": "/repo/app/main.py::Engine.run",
                "relevance": 7,
            }
        ]
    )
    repo = KnowledgeRepository(db)

    rows = await repo.find_code_citations(tokens=["run", "engine"], limit=3)

    assert len(db.query_calls) == 1
    call = db.query_calls[0]
    assert call["operation"] == "repo_find_code_citations"
    assert call["params"]["tokens"] == ["run", "engine"]
    assert call["params"]["limit"] == 3
    assert "toInteger(coalesce(e.line, 1)) as line" in call["query"]
    assert rows[0]["file_path"] == "/repo/app/main.py"
    assert rows[0]["line"] == 42
