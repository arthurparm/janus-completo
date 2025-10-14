import asyncio
import logging
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from prometheus_client import Counter

from app.config import settings

logger = logging.getLogger(__name__)

# Métricas
_MESSAGES_PUBLISHED = Counter("broker_messages_published_total", "Total de mensagens publicadas", ["queue"])
_CONNECTION_ERRORS = Counter("broker_connection_errors_total", "Total de erros de conexão com o broker")

class MessageBroker:
    """
    Gerencia a conexão e as operações com o message broker (RabbitMQ).
    """
    _connection: Optional[AbstractRobustConnection] = None
    _connection_lock = asyncio.Lock()

    async def connect(self):
        """Estabelece a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return
        async with self._connection_lock:
            if self._connection and not self._connection.is_closed:
                return
            logger.info("Conectando ao RabbitMQ...")
            try:
                self._connection = await aio_pika.connect_robust(
                    settings.RABBITMQ_URL,
                    client_properties={"connection_name": "janus_system"}
                )
                logger.info("Conexão com RabbitMQ estabelecida com sucesso.")
            except Exception as e:
                _CONNECTION_ERRORS.inc()
                logger.critical(f"FATAL: Não foi possível conectar ao RabbitMQ: {e}", exc_info=True)
                raise ConnectionError(f"Falha ao conectar ao RabbitMQ: {e}") from e

    async def close(self):
        """Fecha a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            logger.info("Conexão com RabbitMQ fechada.")

    async def publish(self, queue_name: str, message: str):
        """Publica uma mensagem em uma fila."""
        await self.connect()
        async with self._connection.channel() as channel:
            await channel.declare_queue(queue_name, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(body=message.encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=queue_name,
            )
            _MESSAGES_PUBLISHED.labels(queue_name).inc()

    async def get_queue_info(self, queue_name: str) -> Optional[dict]:
        """Obtém informações sobre uma fila."""
        await self.connect()
        async with self._connection.channel() as channel:
            queue = await channel.declare_queue(queue_name, durable=True)
            return {
                "name": queue.name,
                "messages": queue.declaration_result.message_count,
                "consumers": queue.declaration_result.consumer_count,
            }

    async def health_check(self) -> bool:
        """Verifica a saúde da conexão."""
        try:
            await self.connect()
            return not self._connection.is_closed
        except Exception:
            return False


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_broker_instance: Optional[MessageBroker] = None


async def initialize_broker():
    """Inicializa a instância singleton do MessageBroker."""
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = MessageBroker()
        await _broker_instance.connect()


async def close_broker():
    """Fecha a conexão da instância singleton."""
    if _broker_instance:
        await _broker_instance.close()


async def get_broker() -> MessageBroker:
    """Função getter para injeção de dependência."""
    if _broker_instance is None:
        await initialize_broker()
    return _broker_instance
