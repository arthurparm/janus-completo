import json

import pytest

from app.core.workers.async_consolidation_worker import publish_consolidation_task

try:
    import msgpack
except Exception:
    msgpack = None

class FakeBroker:
    def __init__(self):
        self.published = []

    async def publish(
        self,
        queue_name: str,
        message: str | bytes,
        priority: int | None = None,
        headers: dict | None = None,
        use_msgpack: bool = False,
    ):
        self.published.append({
            "queue": queue_name,
            "message": message,
            "priority": priority,
            "headers": headers,
            "use_msgpack": use_msgpack,
        })


@pytest.mark.asyncio
async def test_publish_consolidation_task_enqueues_valid_message(monkeypatch):
    import app.core.workers.async_consolidation_worker as acw

    fake_broker = FakeBroker()
    async def fake_get_broker():
        return fake_broker
    monkeypatch.setattr(acw, "get_broker", fake_get_broker)

    payload = {
        "mode": "single",
        "experience_id": "exp-1",
        "experience_content": "Some valuable knowledge",
        "metadata": {"origin": "router"}
    }

    result = await publish_consolidation_task(payload)
    assert result["status"] == "ok"
    assert isinstance(result["task_id"], str) and len(result["task_id"]) > 0

    # Examine published message
    from app.models.schemas import QueueName
    assert len(fake_broker.published) == 1
    pub = fake_broker.published[0]
    assert pub["queue"] == QueueName.KNOWLEDGE_CONSOLIDATION.value

    assert pub["use_msgpack"] is True
    raw = pub["message"]
    if msgpack is not None:
        msg = msgpack.unpackb(raw, raw=False)
    else:
        msg = json.loads(raw.decode("utf-8"))
    assert msg["task_type"] == "knowledge_consolidation"
    assert msg["payload"]["mode"] == "single"
    assert msg["payload"]["experience_id"] == "exp-1"
