import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Router worker tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

import app.core.workers.router_worker as router_worker
from app.core.workers.router_worker import _contains_knowledge_payload
from app.models.schemas import TaskMessage, TaskState


def make_state(**kwargs) -> TaskState:
    base = dict(
        original_goal="",
        data_payload={},
        history=[],
        status="success",
    )
    base.update(kwargs)
    return TaskState(**base)


def test_contains_knowledge_tool_output_long_text():
    text = "x" * 300
    state = make_state(data_payload={"tool_output": text})
    assert _contains_knowledge_payload(state) is True


def test_contains_knowledge_sandbox_output_sufficient_and_no_error():
    text = "resultado do sandbox" * 5  # >= 64 chars
    state = make_state(data_payload={"sandbox_output": text, "sandbox_error": ""})
    assert _contains_knowledge_payload(state) is True


def test_contains_knowledge_sandbox_has_error_should_not_trigger():
    text = "resultado do sandbox" * 5
    state = make_state(data_payload={"sandbox_output": text, "sandbox_error": "Traceback..."})
    assert _contains_knowledge_payload(state) is False


def test_contains_knowledge_goal_keywords_pt_en():
    state_pt = make_state(original_goal="Pesquisar artigo PDF sobre context learning")
    state_en = make_state(original_goal="Do research and read docs about RAG")
    assert _contains_knowledge_payload(state_pt) is True
    assert _contains_knowledge_payload(state_en) is True


def test_contains_knowledge_negative_cases():
    # Short tool output, short sandbox, no goal match
    state = make_state(original_goal="Implementar função", data_payload={"tool_output": "ok", "sandbox_output": "ok"})
    assert _contains_knowledge_payload(state) is False


@pytest.mark.asyncio
async def test_router_terminal_task_to_router_is_consumed_without_republish(monkeypatch):
    publishes = []

    class _FakeBroker:
        async def publish(self, **kwargs):
            publishes.append(kwargs)

    class _FakeCollaborationService:
        pass_task_calls = 0
        finalized_calls = 0

        def __init__(self, *_args, **_kwargs):
            pass

        async def pass_task(self, _state):
            type(self).pass_task_calls += 1

        def maybe_finalize_autonomy_goal(self, _state):
            type(self).finalized_calls += 1

    monkeypatch.setattr(router_worker, "get_broker", AsyncMock(return_value=_FakeBroker()))
    monkeypatch.setattr(router_worker, "CollaborationService", _FakeCollaborationService)

    msg = TaskMessage(
        task_id="t1",
        task_type="task_state",
        payload={
            "task_state": TaskState(
                task_id="t1",
                original_goal="Implementar função",
                next_agent_role="router",
                status="completed",
                data_payload={},
                meta={"autonomy": {"goal_id": "g1"}},
                history=[],
            ).model_dump()
        },
    )

    await router_worker.process_router_task(msg)

    assert _FakeCollaborationService.pass_task_calls == 0
    assert _FakeCollaborationService.finalized_calls == 1
    assert len(publishes) == 1  # distillation side-effect on terminal success


@pytest.mark.asyncio
async def test_router_corrects_non_terminal_self_loop_and_republishes(monkeypatch):
    publishes = []

    class _FakeBroker:
        async def publish(self, **kwargs):
            publishes.append(kwargs)

    class _FakeCollaborationService:
        last_state = None

        def __init__(self, *_args, **_kwargs):
            pass

        async def pass_task(self, state):
            type(self).last_state = state

        def maybe_finalize_autonomy_goal(self, _state):
            raise AssertionError("should not finalize non-terminal task")

    monkeypatch.setattr(router_worker, "get_broker", AsyncMock(return_value=_FakeBroker()))
    monkeypatch.setattr(router_worker, "CollaborationService", _FakeCollaborationService)

    msg = TaskMessage(
        task_id="t2",
        task_type="task_state",
        payload={
            "task_state": TaskState(
                task_id="t2",
                original_goal="Implementar função",
                next_agent_role="router",
                status="in_progress",
                data_payload={},
                history=[],
            ).model_dump()
        },
    )

    await router_worker.process_router_task(msg)

    assert _FakeCollaborationService.last_state is not None
    assert _FakeCollaborationService.last_state.next_agent_role == "thinker"
    assert publishes == []  # no knowledge side effects on non-terminal state
