import sys
import types
from unittest.mock import AsyncMock

import pytest

from app.core.tools import agent_tools


def test_write_file_accepts_only_file_path(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_tools, "WORKSPACE_ROOT", tmp_path)

    result = agent_tools.write_file.func(
        file_path="notes.txt",
        content="hello",
        overwrite=True,
    )

    assert "salvo com sucesso" in result.lower()
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"

    with pytest.raises(TypeError):
        agent_tools.write_file.func(path="legacy.txt", content="x", overwrite=True)  # type: ignore[call-arg]


def test_read_file_schema_and_contract_are_canonical(monkeypatch):
    schema = agent_tools.ReadFileInput.model_json_schema()
    assert "file_path" in schema["properties"]
    assert "path" not in schema["properties"]

    captured: dict[str, str] = {}

    def fake_read_file(file_path: str) -> str:
        captured["file_path"] = file_path
        return "ok"

    monkeypatch.setattr(agent_tools.filesystem_manager, "read_file", fake_read_file)

    assert agent_tools.read_file.invoke({"file_path": "README.md"}) == "ok"
    assert captured["file_path"] == "README.md"

    with pytest.raises(Exception):
        agent_tools.read_file.invoke({"path": "README.md"})


@pytest.mark.asyncio
async def test_query_knowledge_graph_accepts_only_query(monkeypatch):
    fake_module = types.ModuleType("app.core.memory.knowledge_graph_manager")
    fake_search = AsyncMock(return_value=[{"summary": "Resultado A"}])
    fake_module.knowledge_graph_manager = types.SimpleNamespace(semantic_search=fake_search)
    monkeypatch.setitem(sys.modules, "app.core.memory.knowledge_graph_manager", fake_module)

    result = await agent_tools.query_knowledge_graph.ainvoke({"query": "python"})

    assert "Conhecimento encontrado" in result
    fake_search.assert_awaited_once_with("python", limit=10)

    with pytest.raises(Exception):
        await agent_tools.query_knowledge_graph.ainvoke({"consulta": "python"})


def test_agent_tool_registries_are_importable():
    tool_names = {tool.name for tool in agent_tools.unified_tools}
    meta_tool_names = {tool.name for tool in agent_tools.meta_agent_tools}

    assert "write_file" in tool_names
    assert "read_file" in tool_names
    assert "query_knowledge_graph" in tool_names
    assert "analyze_memory_for_failures" in meta_tool_names
