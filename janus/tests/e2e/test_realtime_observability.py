import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.infrastructure.message_broker import MessageBroker


@pytest.mark.asyncio
async def test_realtime_events_endpoint(client_test, base_url):
    """
    Testa o endpoint de streaming de eventos em tempo real.
    Verifica se eventos publicados na exchange chegam no cliente SSE.
    """
    conversation_id = "test-conv-realtime"

    # Mock do Broker
    mock_broker = AsyncMock(spec=MessageBroker)
    asyncio.Queue()

    # Simula start_subscription colocando dados na queue interna do mock
    # A implementação real do ChatService usa um callback. Precisamos capturar esse callback.
    captured_callback = None

    def side_effect_start_subscription(exchange_name, routing_key, callback, queue_name=""):
        nonlocal captured_callback
        captured_callback = callback
        # Retorna uma task fake
        return asyncio.create_task(asyncio.sleep(0.1))

    mock_broker.start_subscription.side_effect = side_effect_start_subscription
    mock_broker.connect.return_value = None
    mock_broker._connection = MagicMock()

    # Patch do get_broker para retornar nosso mock
    with patch("app.core.infrastructure.message_broker.get_broker", new=AsyncMock(return_value=mock_broker)):

        # 1. Inicia conexão SSE em background (simulando cliente)
        async def connect_sse():
            async with AsyncClient(base_url=base_url) as ac:
                async with ac.stream("GET", f"/api/v1/chat/{conversation_id}/events") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            yield line

        # Generator do SSE
        sse_gen = connect_sse()

        # 2. Aguarda conexão ser estabelecida (o endpoint chama get_broker e start_subscription)
        # Como é async, precisamos dar um tempinho ou fazer polling
        # Mas o sse_gen precisa ser iterado para o código rodar.

        # Vamos iterar manualmente
        first_event = await anext(sse_gen)
        # O primeiro evento é "event: connected\ndata: {}" -> linha "data: {}"
        assert "data: {}" in first_event

        # Agora o subscription deve ter sido chamado
        assert mock_broker.start_subscription.called
        assert captured_callback is not None

        # 3. Simula chegada de um evento do RabbitMQ
        event_payload = {
            "task_id": "task-123",
            "agent_role": "coder",
            "event_type": "AgentThinking",
            "content": "Thinking about the code...",
            "timestamp": 1234567890.0
        }

        # Invoca o callback que o ChatService registrou
        await captured_callback(event_payload)

        # 4. Verifica se o evento chegou no SSE
        second_event = await anext(sse_gen)
        print(f"Received SSE: {second_event}")

        assert "data:" in second_event
        data_json = json.loads(second_event.replace("data: ", ""))
        assert data_json["agent"] == "coder"
        assert data_json["content"] == "Thinking about the code..."

        print("✅ Real-time event propagation verifyied!")

