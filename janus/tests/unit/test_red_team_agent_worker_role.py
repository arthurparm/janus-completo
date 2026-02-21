from unittest.mock import AsyncMock, patch

import pytest

from app.core.workers.red_team_agent_worker import RED_TEAM_ROLE, process_red_team_task
from app.models.schemas import TaskMessage, TaskState


@pytest.mark.asyncio
async def test_red_team_worker_forces_current_role_before_routing():
    state = TaskState(
        task_id="task-rt-1",
        original_goal="Audit login handler",
        data_payload={
            "code_snippets": {"login.py": "def login(user):\n    return user"},
            "context": "",
        },
    )
    task = TaskMessage(
        task_id="task-rt-1",
        task_type="task_state",
        payload={"task_state": state.model_dump()},
        timestamp=0.0,
    )

    with (
        patch(
            "app.core.workers.red_team_agent_worker._build_security_prompt",
            new=AsyncMock(return_value="audit prompt"),
        ),
        patch("app.core.workers.red_team_agent_worker.LLMService") as mock_llm_cls,
        patch("app.core.workers.red_team_agent_worker.CollaborationService") as mock_collab_cls,
    ):
        mock_llm = mock_llm_cls.return_value
        mock_llm.invoke_llm = AsyncMock(
            return_value={"response": "SAFE: no vulnerabilities", "reasoning": "ok"}
        )

        mock_collab = mock_collab_cls.return_value
        mock_collab.pass_task = AsyncMock()

        await process_red_team_task(task)

        updated_state = mock_collab.pass_task.await_args.args[0]
        assert updated_state.current_agent_role == RED_TEAM_ROLE
        assert updated_state.history[-1].agent_role == RED_TEAM_ROLE
