from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.workers.red_team_agent_worker import _parse_security_assessment, process_red_team_task
from app.models.schemas import TaskMessage, TaskState
from app.services.collaboration_service import CollaborationService


def test_parse_security_assessment_uses_structured_json_payload():
    response_text = """
    ```json
    {
      "decision": "rejected",
      "summary": "Found SQL injection risk",
      "findings": [
        {
          "id": "sqli-1",
          "severity": "high",
          "cwe": "CWE-89",
          "file": "login.py",
          "line": 42,
          "title": "SQL Injection",
          "evidence": "string concatenation in query",
          "fix_hint": "use parameterized query"
        }
      ]
    }
    ```
    """
    decision, findings, summary = _parse_security_assessment(response_text)

    assert decision == "rejected"
    assert summary == "Found SQL injection risk"
    assert len(findings) == 1
    assert findings[0]["id"] == "sqli-1"
    assert findings[0]["severity"] == "high"
    assert findings[0]["cwe"] == "CWE-89"


@pytest.mark.asyncio
async def test_red_team_worker_persists_structured_security_fields():
    state = TaskState(
        task_id="rt-structured-1",
        original_goal="Audit auth module",
        data_payload={
            "code_snippets": {"auth.py": "query = f'SELECT * FROM users WHERE id = {user_id}'"},
            "context": "",
        },
    )
    task = TaskMessage(
        task_id="rt-structured-1",
        task_type="task_state",
        payload={"task_state": state.model_dump()},
        timestamp=0.0,
    )

    llm_payload = {
        "response": (
            '{"decision":"rejected","summary":"Critical issue",'
            '"findings":[{"id":"f-1","severity":"critical","cwe":"CWE-89",'
            '"file":"auth.py","line":7,"title":"SQL injection","evidence":"unsafe query"}]}'
        ),
        "reasoning": "analysis",
    }

    with (
        patch(
            "app.core.workers.red_team_agent_worker._build_security_prompt",
            new=AsyncMock(return_value="prompt"),
        ),
        patch("app.core.workers.red_team_agent_worker.LLMService") as mock_llm_cls,
        patch("app.core.workers.red_team_agent_worker.CollaborationService") as mock_collab_cls,
    ):
        mock_llm = mock_llm_cls.return_value
        mock_llm.invoke_llm = AsyncMock(return_value=llm_payload)
        mock_collab = mock_collab_cls.return_value
        mock_collab.pass_task = AsyncMock()

        await process_red_team_task(task)

        updated_state = mock_collab.pass_task.await_args.args[0]
        assert updated_state.security_decision == "rejected"
        assert updated_state.security_cycle_count == 1
        assert updated_state.blocked_reason == "blocking_security_findings"
        assert updated_state.data_payload.audit_passed is False
        assert len(updated_state.data_payload.security_findings) == 1
        assert updated_state.data_payload.security_findings[0]["severity"] == "critical"
        assert updated_state.next_agent_role == "coder"


@pytest.mark.asyncio
async def test_collaboration_service_routes_blue_team_to_dedicated_queue():
    state = TaskState(task_id="flow-1", original_goal="goal", next_agent_role="blue_team")
    broker = MagicMock()
    broker.publish = AsyncMock()

    with patch("app.services.collaboration_service.get_broker", AsyncMock(return_value=broker)):
        service = CollaborationService(repo=MagicMock())
        queue = await service.pass_task(state)

    assert queue == "janus.tasks.agent.blue_team"
    broker.publish.assert_awaited_once()
    assert broker.publish.await_args.kwargs["queue_name"] == "janus.tasks.agent.blue_team"


@pytest.mark.asyncio
async def test_collaboration_service_routes_security_judge_to_dedicated_queue():
    state = TaskState(task_id="flow-2", original_goal="goal", next_agent_role="security_judge")
    broker = MagicMock()
    broker.publish = AsyncMock()

    with patch("app.services.collaboration_service.get_broker", AsyncMock(return_value=broker)):
        service = CollaborationService(repo=MagicMock())
        queue = await service.pass_task(state)

    assert queue == "janus.tasks.agent.security_judge"
    broker.publish.assert_awaited_once()
    assert broker.publish.await_args.kwargs["queue_name"] == "janus.tasks.agent.security_judge"
