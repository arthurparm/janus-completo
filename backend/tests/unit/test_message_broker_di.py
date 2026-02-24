
from unittest.mock import AsyncMock, patch

import pytest

from app.core.infrastructure.message_broker import MessageBroker


class MockSettings:
    RABBITMQ_USER = "mock_user"
    RABBITMQ_PASSWORD = "mock_pass"
    RABBITMQ_HOST = "mock_host"
    RABBITMQ_PORT = 5672
    RABBITMQ_MANAGEMENT_PORT = 15672
    RABBITMQ_QUEUE_CONFIG = {}
    BROKER_USE_MSGPACK = True

@pytest.mark.asyncio
async def test_message_broker_di_connect():
    """
    Verify that MessageBroker uses injected settings and connection factory.
    """
    mock_settings = MockSettings()
    mock_factory = AsyncMock()

    broker = MessageBroker(config=mock_settings, connection_factory=mock_factory)
    await broker.connect()

    # Verify factory called with mock settings
    expected_url = f"amqp://{mock_settings.RABBITMQ_USER}:{mock_settings.RABBITMQ_PASSWORD}@{mock_settings.RABBITMQ_HOST}:{mock_settings.RABBITMQ_PORT}/"
    mock_factory.assert_called_once()
    call_args = mock_factory.call_args
    assert call_args[0][0] == expected_url, f"Expected URL {expected_url}, but got {call_args[0][0]}"

@pytest.mark.asyncio
async def test_message_broker_di_defaults():
    """
    Verify that MessageBroker falls back to global settings and default factory if no config is provided.
    """
    with patch("app.core.infrastructure.message_broker.aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        # Patch global settings to ensure we are testing defaults
        with patch("app.core.infrastructure.message_broker.settings") as global_settings:
            global_settings.RABBITMQ_USER = "global_user"
            global_settings.RABBITMQ_PASSWORD = "global_pass"
            global_settings.RABBITMQ_HOST = "global_host"
            global_settings.RABBITMQ_PORT = 5672

            broker = MessageBroker()
            await broker.connect()

            expected_url = "amqp://global_user:global_pass@global_host:5672/"
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args
            assert call_args[0][0] == expected_url
