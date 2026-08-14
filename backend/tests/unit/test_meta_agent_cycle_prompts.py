import importlib
from typing import Any
from unittest.mock import AsyncMock

import pytest

meta_agent_cycle = importlib.import_module("app.core.agents.meta_agent_cycle")


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        del args


class _Driver:
    def __init__(self, session: object) -> None:
        self._session = session

    def session(self) -> _SessionContext:
        return _SessionContext(self._session)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_meta_cycle_awaits_plan_and_act_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_get = AsyncMock(side_effect=["prompt de plano", "prompt de análise"])
    agent_run = AsyncMock(
        side_effect=[{"answer": "plano real"}, {"answer": "análise real"}]
    )
    memory = type("Memory", (), {"amemorize": AsyncMock()})()
    query_result = type("QueryResult", (), {"list": AsyncMock(return_value=[{"insight": "lição"}])})()
    session = type("Session", (), {"run": AsyncMock(return_value=query_result)})()

    monkeypatch.setattr(meta_agent_cycle.prompt_loader, "get", prompt_get)
    monkeypatch.setattr(meta_agent_cycle.agent_manager, "arun_agent", agent_run)
    monkeypatch.setattr(meta_agent_cycle, "get_memory_db", AsyncMock(return_value=memory))
    monkeypatch.setattr(
        meta_agent_cycle,
        "graph_db",
        type("Graph", (), {"get_driver": lambda self: _Driver(session)})(),
    )

    shared: dict[str, Any] = {
        "hypothesis": None,
        "actions": [],
        "observations": [],
        "refinements": [],
        "iteration": 1,
    }

    should_continue = await meta_agent_cycle._execute_meta_cycle(shared)

    assert should_continue is True
    assert prompt_get.await_args_list[0].args == ("meta_agent_plan",)
    assert prompt_get.await_args_list[1].args == ("meta_agent_act",)
    assert prompt_get.await_args_list[1].kwargs == {
        "variables": {"learning_lessons": "lição"}
    }
    assert agent_run.await_args_list[0].kwargs["question"] == "prompt de plano"
    assert agent_run.await_args_list[1].kwargs["question"] == "prompt de análise"
    assert shared["hypothesis"] == "plano real"
