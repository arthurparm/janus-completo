import os
import sys
from unittest.mock import patch

import pytest

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.core.workers.codex_worker import process_codex_task
from app.models.schemas import TaskMessage


@pytest.mark.asyncio
async def test_codex_worker_executes_when_approved():
    with patch("app.core.tools.external_cli_tools._run_command") as mock_run, patch(
        "app.core.workers.codex_worker.CollaborationService"
    ) as mock_service_cls:
        mock_run.return_value = "Patch sugerido pelo Codex"
        mock_service = mock_service_cls.return_value

        task_message = TaskMessage(
            task_id="test-task-123",
            task_type="codex_fix",
            payload={
                "goal": "Corrigir erro de sintaxe",
                "instruction": "O arquivo x.py tem um erro na linha 10",
                "approved": True,
            },
            timestamp=1234567890.0,
        )

        await process_codex_task(task_message)

        mock_service.add_artifact.assert_called_once()
        artifact_value = mock_service.add_artifact.call_args.kwargs["value"]
        assert "Patch sugerido" in artifact_value["result"]
        assert artifact_value["approved"] is True


@pytest.mark.asyncio
async def test_codex_worker_requires_approval_by_default():
    with patch("app.core.tools.external_cli_tools._run_command") as mock_run, patch(
        "app.core.workers.codex_worker.CollaborationService"
    ) as mock_service_cls:
        mock_run.return_value = "NÃO deveria executar"
        mock_service = mock_service_cls.return_value

        task_message = TaskMessage(
            task_id="test-task-456",
            task_type="codex_fix",
            payload={
                "goal": "Corrigir erro de sintaxe",
                "instruction": "O arquivo x.py tem um erro na linha 10",
            },
            timestamp=1234567890.0,
        )

        await process_codex_task(task_message)

        mock_service.add_artifact.assert_called_once()
        artifact_value = mock_service.add_artifact.call_args.kwargs["value"]
        assert "Tool requires confirmation" in artifact_value["result"]
