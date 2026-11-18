import asyncio
from unittest.mock import AsyncMock

import pytest

import app.services.knowledge_service as knowledge_module
from app.services.knowledge_service import KnowledgeService


class _FakeRepo:
    def __init__(self):
        self.clear_calls = 0
        self.bulk_calls = 0
        self.saved_parsers: list[object] = []

    async def clear_code_entities(self):
        self.clear_calls += 1
        await asyncio.sleep(0.05)

    async def save_code_structure(self, parser):
        self.saved_parsers.append(parser)

    async def bulk_merge_calls(self, calls):
        self.bulk_calls += 1


@pytest.mark.asyncio
async def test_index_codebase_serializes_concurrent_runs(monkeypatch):
    repo = _FakeRepo()
    service = KnowledgeService(repo)
    repair_mock = AsyncMock(return_value={"repaired": 0, "connected": 0, "provenance_links": 0, "symbol_links": 0})
    monkeypatch.setattr(service, "repair_self_memory_graph", repair_mock)
    monkeypatch.setattr(knowledge_module.code_analysis_service, "find_python_files", lambda _: [])

    result_a, result_b = await asyncio.gather(service.index_codebase(), service.index_codebase())

    assert result_a["summary"] == result_b["summary"]
    assert repo.clear_calls == 1
    assert repo.bulk_calls == 1
    assert repair_mock.await_count == 1


@pytest.mark.asyncio
async def test_repair_self_memory_graph_relinks_owner_and_provenance(monkeypatch):
    service = KnowledgeService(_FakeRepo())
    captured_ops: list[str] = []

    class _FakeGraph:
        async def query(self, query: str, params: dict | None = None, *args, **kwargs):
            operation = str(kwargs.get("operation") or "")
            captured_ops.append(operation)
            if operation == "knowledge_self_memory_fetch":
                return [
                    {
                        "node_id": "1",
                        "file_path": "backend/app/services/example.py",
                        "summary_version": "v2",
                        "sha_after": "abc123",
                        "source_experience_id": "exp-1",
                        "symbols": ["ExampleService"],
                        "updated_at": 20,
                    },
                    {
                        "node_id": "2",
                        "file_path": "frontend/src/app/login.ts",
                        "summary_version": "v2",
                        "sha_after": None,
                        "source_experience_id": None,
                        "symbols": ["LoginComponent"],
                        "updated_at": 10,
                    },
                ]
            if operation == "knowledge_self_memory_owner_link_existing":
                if params and params.get("node_id") == "1":
                    return [{"owner_links": 1}]
                return [{"owner_links": 0}]
            if operation == "knowledge_self_memory_owner_link_fallback":
                return [{"owner_links": 1}]
            if operation == "knowledge_self_memory_function_link":
                if params and params.get("node_id") == "1":
                    return [{"symbol_links": 1}]
                return [{"symbol_links": 0}]
            if operation == "knowledge_self_memory_class_link":
                return [{"symbol_links": 0}]
            if operation == "knowledge_self_memory_provenance_link":
                return [{"provenance_links": 1}]
            return [{"ok": True}]

    async def _fake_get_graph_db():
        return _FakeGraph()

    monkeypatch.setattr(knowledge_module, "get_graph_db", _fake_get_graph_db)

    result = await service.repair_self_memory_graph(limit=10)

    assert result["repaired"] == 2
    assert result["connected"] == 2
    assert result["provenance_links"] == 1
    assert result["symbol_links"] == 1
    assert "knowledge_self_memory_owner_link_fallback" in captured_ops
    assert "knowledge_self_memory_experience_upsert" in captured_ops
    assert "knowledge_self_memory_provenance_link" in captured_ops
