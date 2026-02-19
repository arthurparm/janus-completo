import json
from unittest.mock import AsyncMock

import pytest

from app.core.autonomy import planner


@pytest.mark.asyncio
async def test_replan_goal_without_goal_aborts_safely():
    llm_service = AsyncMock()
    llm_service.invoke_llm = AsyncMock(return_value={"response": '{"action":"IGNORE"}'})

    decision = await planner.replan_goal(
        goal=None,
        failed_step={"tool": "get_system_info", "args": {}},
        error_msg="boom",
        remaining_steps=[],
        llm_service=llm_service,
        policy=None,
    )

    assert decision == {"action": "ABORT", "reason": "missing_goal"}
    llm_service.invoke_llm.assert_not_called()


@pytest.mark.asyncio
async def test_verify_outcome_without_goal_fails_safely():
    llm_service = AsyncMock()
    llm_service.invoke_llm = AsyncMock(return_value={"response": '{"success": true}'})

    verification = await planner.verify_outcome(
        goal=None,
        step={"tool": "get_system_info", "args": {}},
        result={"ok": True},
        error=None,
        llm_service=llm_service,
    )

    assert verification == {"success": False, "reason": "Missing active goal"}
    llm_service.invoke_llm.assert_not_called()


@pytest.mark.asyncio
async def test_build_replanning_prompt_uses_fallback_goal_title(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_get_formatted_prompt(name: str, **kwargs):
        captured["name"] = name
        captured["ctx"] = kwargs["ctx"]
        return "prompt"

    monkeypatch.setattr(planner, "get_formatted_prompt", fake_get_formatted_prompt)

    built = await planner._build_replanning_prompt(
        goal=None,
        failed_step={"tool": "x"},
        error_msg="error",
        remaining_steps=[{"tool": "y"}],
        tools=["x", "y"],
    )

    ctx = json.loads(captured["ctx"])
    assert built == "prompt"
    assert captured["name"] == "autonomy_replanner"
    assert ctx["goal"] == "No active goal"
