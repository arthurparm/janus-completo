import json
import pytest

from app.models.schemas import TaskMessage, TaskState


class FakeBroker:
    def __init__(self):
        self.published = []

    async def publish(self, queue_name: str, message: str, priority: int | None = None, headers: dict | None = None):
        self.published.append({
            "queue": queue_name,
            "message": message,
            "priority": priority,
            "headers": headers,
        })


@pytest.mark.asyncio
async def test_router_side_publishes_consolidation(monkeypatch):
    # Patch broker inside router module
    import app.core.workers.router_worker as rw

    fake_broker = FakeBroker()
    async def fake_get_broker():
        return fake_broker
    monkeypatch.setattr(rw, "get_broker", fake_get_broker)

    # Build TaskState that should trigger knowledge consolidation
    state = TaskState(
        original_goal="Research and read docs about vector DBs",
        data_payload={"tool_output": "x" * 300},
        status="success",
        history=[{"agent_role": "code_agent", "action": "coded", "timestamp": 0.0}],
    )
    task = TaskMessage(
        task_id=state.task_id,
        task_type="route",
        payload={"task_state": state.model_dump()},
        timestamp=0.0,
    )

    await rw.process_router_task(task)

    # Assert a publish occurred to consolidation queue
    assert len(fake_broker.published) >= 1
    pub = fake_broker.published[0]
    from app.models.schemas import QueueName
    assert pub["queue"] == QueueName.KNOWLEDGE_CONSOLIDATION.value

    # Assert payload is a TaskMessage JSON with mode single and content present
    payload = json.loads(pub["message"])
    assert payload["task_type"] == "knowledge_consolidation"
    assert payload["payload"]["mode"] == "single"
    content = payload["payload"]["experience_content"]
    assert isinstance(content, str) and len(content) >= 256