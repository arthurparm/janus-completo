import pytest

from app.models.schemas import TaskMessage


class FakeMemoryService:
    def __init__(self):
        self.saved = []

    async def add_experience(self, type: str, content: str, metadata: dict):
        self.saved.append({"type": type, "content": content, "metadata": metadata})


class Capture:
    def __init__(self):
        self.modes = []

    async def publish(self, mode: str = "single"):
        self.modes.append(mode)


@pytest.mark.asyncio
async def test_process_failure_event_persists_and_triggers_cycle(monkeypatch):
    # Import late to allow monkeypatching module state
    import app.core.workers.meta_agent_worker as maw

    # Inject fake memory service and bypass initializer
    fake_mem = FakeMemoryService()
    maw._memory_service = fake_mem
    monkeypatch.setattr(maw, "_ensure_memory_initialized", lambda: None)

    # Capture publish_meta_agent_cycle calls
    capture = Capture()
    async def fake_publish(mode: str = "single", priority: int = 5):
        await capture.publish(mode)
        return "task-id"
    monkeypatch.setattr(maw, "publish_meta_agent_cycle", fake_publish)

    payload = {
        "reason": "docker_timeout",
        "score": 0.82,
        "origin": "sandbox_agent",
        "timestamp": "2025-01-01T12:00:00Z",
        "context": {
            "conversation_id": "conv-1",
            "interaction_id": "int-1",
            "task": "Run code in sandbox"
        },
    }
    task = TaskMessage(task_id="evt-123", task_type="failure_detected", payload=payload, timestamp=0.0)

    await maw.process_failure_event(task)

    # Assert experience persisted with critical fields
    assert len(fake_mem.saved) == 1
    exp = fake_mem.saved[0]
    assert exp["type"] == "action_failure"
    assert "Failure detected" in exp["content"]
    md = exp["metadata"]
    assert md["status"] == "failure"
    assert md["error_type"] == "docker_timeout"
    assert md["component"] == "sandbox_agent"
    assert md["task_id"] == "evt-123"
    assert md["queue"]

    # Assert meta-agent cycle was published with correct mode
    assert capture.modes == ["failure_event"]