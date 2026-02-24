import json

import pytest

from app.core.infrastructure import reasoning_core


class _AsyncExecutor:
    def __init__(self, output: str = "ok-async"):
        self.output = output
        self.last_payload = None

    async def ainvoke(self, payload):
        self.last_payload = payload
        return {"output": self.output}


class _SyncExecutor:
    def __init__(self, output: str = "ok-sync"):
        self.output = output
        self.last_payload = None

    def invoke(self, payload):
        self.last_payload = payload
        return {"output": self.output}


@pytest.mark.asyncio
async def test_reasoning_session_ensure_agent_is_idempotent(monkeypatch):
    calls = {"provider": 0, "agent_factory": 0}

    async def fake_provider(**kwargs):
        assert kwargs["priority"] == reasoning_core.ModelPriority.HIGH_QUALITY
        calls["provider"] += 1
        return object()

    async def fake_prompt(prompt_name: str):
        assert prompt_name == "reasoning_session"
        return "Pergunta: {input}"

    def fake_create_react_agent(llm, tools, prompt):
        calls["agent_factory"] += 1
        return _AsyncExecutor()

    monkeypatch.setattr(reasoning_core, "get_prompt", fake_prompt)
    monkeypatch.setattr(reasoning_core, "create_react_agent", fake_create_react_agent)

    session = reasoning_core.ReasoningSession(fake_provider, [])
    await session._ensure_agent()
    await session._ensure_agent()

    assert calls["provider"] == 1
    assert calls["agent_factory"] == 1


@pytest.mark.asyncio
async def test_solve_question_uses_async_executor_path(monkeypatch):
    executor = _AsyncExecutor(output="resposta-async")

    async def fake_provider(**kwargs):
        return object()

    async def fake_prompt(prompt_name: str):
        return "Pergunta: {input}"

    monkeypatch.setattr(reasoning_core, "get_prompt", fake_prompt)
    monkeypatch.setattr(reasoning_core, "create_react_agent", lambda *args, **kwargs: executor)

    session = reasoning_core.ReasoningSession(fake_provider, [])
    result = await session.solve_question("qual o status?")

    assert result == "resposta-async"
    assert executor.last_payload == {"input": "qual o status?"}


@pytest.mark.asyncio
async def test_solve_question_falls_back_to_sync_invoke(monkeypatch):
    executor = _SyncExecutor(output="resposta-sync")

    async def fake_provider(**kwargs):
        return object()

    async def fake_prompt(prompt_name: str):
        return "Pergunta: {input}"

    monkeypatch.setattr(reasoning_core, "get_prompt", fake_prompt)
    monkeypatch.setattr(reasoning_core, "create_react_agent", lambda *args, **kwargs: executor)

    session = reasoning_core.ReasoningSession(fake_provider, [])
    result = await session.solve_question("rodou sync?")

    assert result == "resposta-sync"
    assert executor.last_payload == {"input": "rodou sync?"}


@pytest.mark.asyncio
async def test_solve_question_returns_controlled_error_on_executor_failure(monkeypatch):
    class _BrokenExecutor:
        async def ainvoke(self, payload):
            raise RuntimeError("executor-failed")

    async def fake_provider(**kwargs):
        return object()

    async def fake_prompt(prompt_name: str):
        return "Pergunta: {input}"

    monkeypatch.setattr(reasoning_core, "get_prompt", fake_prompt)
    monkeypatch.setattr(reasoning_core, "create_react_agent", lambda *args, **kwargs: _BrokenExecutor())

    session = reasoning_core.ReasoningSession(fake_provider, [])
    result = await session.solve_question("vai falhar")

    assert "Erro ao processar a pergunta:" in result
    assert "executor-failed" in result


@pytest.mark.asyncio
async def test_search_memory_serializes_results_and_handles_exceptions(monkeypatch):
    class _MemoryDb:
        async def arecall(self, query: str, limit: int):
            assert query == "memory query"
            assert limit == 3
            return [{"content": "match"}]

    async def fake_get_memory_db():
        return _MemoryDb()

    monkeypatch.setattr(reasoning_core, "_resolve_memory_db", fake_get_memory_db)
    ok_payload = await reasoning_core.search_memory.ainvoke({"query": "memory query", "limit": 3})
    parsed_ok = json.loads(ok_payload)
    assert parsed_ok == [{"content": "match"}]

    async def broken_get_memory_db():
        raise ValueError("memory backend unavailable")

    monkeypatch.setattr(reasoning_core, "_resolve_memory_db", broken_get_memory_db)
    error_payload = await reasoning_core.search_memory.ainvoke({"query": "memory query", "limit": 3})
    parsed_error = json.loads(error_payload)
    assert parsed_error["error"] == "memory backend unavailable"
    assert parsed_error["error_type"] == "ValueError"
