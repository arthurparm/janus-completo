import pytest

from app.core.memory import knowledge_graph_manager as kgm


@pytest.mark.asyncio
async def test_index_codebase_uses_only_canonical_index_operations(monkeypatch):
    recorded_calls: list[tuple[str, str]] = []

    def fake_query(operation: str, query: str, params=None):
        recorded_calls.append((operation, query))
        if operation == "merge_calls":
            return []
        return []

    # Avoid filesystem traversal and AST parsing in this unit test.
    monkeypatch.setattr(kgm, "repo", type("Repo", (), {"query": staticmethod(fake_query)})())
    monkeypatch.setattr(kgm.os, "walk", lambda _: [])

    result = kgm.index_codebase()

    assert result["message"] == "Indexação e análise da base de código concluídas."

    allowed_ops = {"ensure_index", "cleanup_code_entities", "merge_calls"}
    assert all(op in allowed_ops for op, _ in recorded_calls)

    index_queries = [query for op, query in recorded_calls if op == "ensure_index"]
    assert len(index_queries) == 8
    assert all("IF NOT EXISTS" in query for query in index_queries)
