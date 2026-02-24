import asyncio
import json
import os
from types import SimpleNamespace
from urllib.parse import urljoin

import pytest
from httpx import AsyncClient

from app.core.infrastructure.message_broker import MessageBroker


@pytest.mark.asyncio
async def test_realtime_events_endpoint(base_url):
    """
    Testa end-to-end: RabbitMQ -> backend SSE -> cliente recebe evento.
    Não usa mocks; publica direto na exchange real.
    """
    conversation_id = "test-conv-realtime"

    # 1) Conecta no SSE do backend
    async def connect_sse():
        api_base = base_url.rstrip("/")
        if api_base.endswith("/api/v1"):
            sse_url = urljoin(api_base + "/", f"chat/{conversation_id}/events")
        else:
            sse_url = urljoin(api_base + "/api/v1/", f"chat/{conversation_id}/events")
        async with AsyncClient() as ac:
            async with ac.stream("GET", sse_url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        yield line

    # 2) Publica evento direto na exchange do RabbitMQ (matching stream_events routing key)
    async def publish_to_broker(payload: dict):
        cfg = SimpleNamespace(
            RABBITMQ_HOST=os.getenv("RABBITMQ_HOST", "localhost"),
            RABBITMQ_PORT=int(os.getenv("RABBITMQ_PORT", "5672")),
            RABBITMQ_USER=os.getenv("RABBITMQ_USER", "janus"),
            RABBITMQ_PASSWORD=os.getenv("RABBITMQ_PASSWORD", "janus_pass"),
            BROKER_USE_MSGPACK=False,
        )
        broker = MessageBroker(config=cfg)
        await broker.publish_to_exchange(
            exchange_name="janus.events",
            routing_key=f"janus.event.conversation.{conversation_id}.{payload.get('event_type','agent_event')}",
            message=payload,
        )
        await asyncio.sleep(0.2)  # tempo para entrega/consumo

    sse_gen = connect_sse()

    # 3) Handshake SSE
    first_event = await anext(sse_gen)
    assert "data: {}" in first_event

    # 4) Envia evento real
    event_payload = {
        "task_id": "task-123",
        "agent_role": "coder",
        "event_type": "AgentThinking",
        "content": "Thinking about the code...",
        "timestamp": 1234567890.0,
        "conversation_id": conversation_id,
    }
    await publish_to_broker(event_payload)

    # 5) Recebe via SSE
    second_event = await anext(sse_gen)
    print(f"Received SSE: {second_event}")

    assert "data:" in second_event
    data_json = json.loads(second_event.replace("data: ", ""))
    assert data_json["agent"] == "coder"
    assert data_json["content"] == "Thinking about the code..."
    assert data_json["event_type"] == "AgentThinking"
    assert data_json["conversation_id"] == conversation_id

    print("✅ Real-time event propagation verified end-to-end!")
